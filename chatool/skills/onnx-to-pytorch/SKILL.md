---
name: "onnx-to-pytorch"
description: "Guide for reverse-engineering ONNX models to pure PyTorch. Invoke when converting ONNX to PyTorch, debugging mismatches, or verifying equivalence."
---

# ONNX to PyTorch Reverse Engineering

## 1. Workflow Overview

```
Explore ONNX graph
      ↓
Map weights to PyTorch modules
      ↓
Implement layer by layer
      ↓
Verify against ONNX (bottom-up)
      ↓
Export to .pt, commit
```

**Commit after every verified submodule.** Use tags for milestones: `git tag v0.1-submodule-verified`.

---

## 2. Exploring the ONNX Graph

### Extract intermediate outputs
```python
import onnx, onnxruntime as ort, copy

model = onnx.load('model.onnx')
model_tmp = copy.deepcopy(model)
model_tmp.graph.output.clear()
model_tmp.graph.output.append(
    onnx.helper.make_tensor_value_info('target_node', onnx.TensorProto.FLOAT, [])
)
onnx.save(model_tmp, '/tmp/extract.onnx')
output = ort.InferenceSession('/tmp/extract.onnx').run(None, inputs)[0]
```

### Key inspection techniques
- Iterate nodes: `for node in model.graph.node`
- Check weights: `for init in model.graph.initializer`
- Trace data flow: `node.input` / `node.output`
- Detect shared weights: same initializer in multiple nodes

### Common patterns
| ONNX Pattern | Likely Meaning |
|-------------|----------------|
| `Conv + Norm + Activation` | ConvBlock |
| `Gemm` (after Flatten) | Linear layer |
| `Add` | Residual or branch merge |
| `Concat` | Feature fusion |
| `Mul` with constant | Scaling (0.5=avg, 0.707=1/√2) |
| `Gather` / `ScatterND` | Indexing / assignment |
| `RandomNormalLike` / `RandomUniformLike` | Random noise injection |

---

## 3. Weight Loading

### Extract weights
```python
weights = {}
for init in onnx.load('model.onnx').graph.initializer:
    weights[init.name] = torch.from_numpy(onnx.numpy_helper.to_array(init).copy()).float()
```

### Common transforms
| ONNX | PyTorch | Note |
|------|---------|------|
| `MatMul` | `nn.Linear` | Often needs `.T` |
| `Gemm` | `nn.Linear` | Check `transB` attribute |
| `Conv` | `nn.Conv` | Usually same shape |
| `LSTM` | Custom or `nn.LSTM` | Stacked [W, R, B] per direction |

### Name mapping
```python
import re

def map_key(onnx_name, prefix_map=None):
    pytorch_name = onnx_name
    if prefix_map:
        for old, new in prefix_map.items():
            pytorch_name = pytorch_name.replace(old, new)
    pytorch_name = re.sub(r'\.(\d+)\.', r'\1.', pytorch_name)
    return pytorch_name.replace('.gamma', '.weight').replace('.beta', '.bias')
```

### ⚠️ Verify values, not just shapes
```python
for name, param in model.named_parameters():
    if name in weights:
        diff = torch.abs(param - weights[name]).max()
        if diff > 1e-6:
            print(f"❌ {name}: max diff = {diff:.8f}")
```

---

## 4. Implementation Checklist

**Never assume defaults. Always read from ONNX attributes.**

### Per-layer checks
| Layer | What to Verify |
|-------|---------------|
| LeakyReLU | slope value (0.01, 0.1, 0.2 are all common) |
| InstanceNorm | weight/bias in initializers? → sets `affine` |
| LayerNorm | epsilon value |
| AdaIN | `(scale + C) * norm + shift` — verify C |
| ConvTranspose | output_padding for exact output size |
| Resize | `mode`, `coordinate_transformation_mode` |
| LSTM | gate order (ONNX uses iofc, not ifoc), bias split |

### Resize coordinate modes
| Mode | Formula |
|------|---------|
| `half_pixel` | `x = (i + 0.5) * L / target - 0.5` |
| `asymmetric` | `x = i * L / target` |
| `align_corners` | `x = i * (L - 1) / (target - 1)` |

⚠️ `exclude_outside=0`: ONNX spec says extrapolate, but onnxruntime may **clamp**. Test empirically.

### Random operations
- `RandomNormalLike` → `torch.randn_like(x) * scale`
- `RandomUniformLike` → `torch.rand_like(x) * scale`
- Set `torch.manual_seed(seed)` for reproducible verification

---

## 5. Verification

### Strategy: bottom-up
1. Individual layers
2. Small blocks
3. Medium modules
4. Large modules
5. End-to-end

### Verify function
```python
def verify(pt, onnx, name=""):
    max_d = torch.abs(pt - onnx).max()
    mean_d = torch.abs(pt - onnx).mean()
    print(f"{name}: max={max_d:.2e} mean={mean_d:.2e}")
    assert max_d < 1e-4
```

### Debug workflow
1. Find first diverging layer (shape or value)
2. Compare inputs to that layer
3. Compare weights
4. Compare operation params (stride, padding, eps, slope, etc.)

### Common failures
| Symptom | Cause | Fix |
|---------|-------|-----|
| Shape mismatch | Wrong slicing or weight transpose | Check dimension indexing |
| Max diff ~1e-3 | Precision, eps, or slope mismatch | Check float32, eps, LeakyReLU slope |
| Max diff > 0.1 | Architecture error | Re-examine graph structure |
| Correlation < 0.95 | Wrong connections | Verify skip connections |
| Periodic artifacts | Bias or small param value mismatch | Compare all parameter values |
| Missing texture / noise | Missing random injection | Check for Random*Like nodes |
| LSTM mismatch | Wrong gate order | Verify iofc vs ifoc |
| Shared branch diff | Missing shared parameter | Check same initializer in multiple nodes |

---

## 6. Refactor to Standard PyTorch

### Export to .pt
```python
# 1. Build architecture with standard init
model = MyModel()
# 2. Load ONNX weights (temporary step)
# ... assign mapped weights ...
# 3. Export
torch.save({'state_dict': model.state_dict()}, 'weights.pt')
```

### Load normally
```python
model = MyModel()
model.load_state_dict(torch.load('weights.pt')['state_dict'])
```

---

## 7. Advanced Topics

### Shared Weights
```python
usage = {}
init_names = {i.name for i in model.graph.initializer}
for node in model.graph.node:
    for inp in node.input:
        if inp in init_names:
            usage.setdefault(inp, []).append(node.name)
for w, nodes in usage.items():
    if len(nodes) > 1:
        print(f"Shared: {w} -> {nodes}")
```

### Signal Processing Ops
ONNX decomposes STFT/ISTFT into primitives:
- `Conv` + `Concat` (magnitude + phase)
- Real/imag weights as separate initializers
- Multiple `Resize` + `Mul` + `Sin`/`Cos` → harmonic generation

### Custom Operations
**Detection signs:** long `Gather`/`ScatterND` chains, `Loop`/`If` nodes, depthwise conv + manual indexing.

**Approach:** extract intermediates → identify math operation → implement → verify shapes.

---

## 8. Quick Reference: ONNX → PyTorch

| ONNX Op | PyTorch | Notes |
|---------|---------|-------|
| Conv | `nn.Conv1d/2d` | groups, padding, dilation |
| ConvTranspose | `nn.ConvTranspose1d` | output_padding |
| Gemm | `nn.Linear` | check transB |
| MatMul | `@` / `matmul` | may need `.T` |
| InstanceNorm | `nn.InstanceNorm1d` | affine? |
| LayerNorm | `F.layer_norm` | normalized_shape |
| LeakyRelu | `F.leaky_relu(x, slope)` | read slope from attrs |
| Resize | `F.interpolate` | mode, coord_transform_mode |
| LSTM | `nn.LSTM` or custom | gate order: iofc |
| Gather | indexing | check axis |
| ScatterND | assignment | check indices shape |
| CumSum | `torch.cumsum` | check axis |
| RandomNormalLike | `torch.randn_like` | set seed for reproducibility |
| RandomUniformLike | `torch.rand_like` | set seed for reproducibility |
