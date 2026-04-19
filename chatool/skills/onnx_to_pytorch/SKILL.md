---
name: "onnx_to_pytorch"
description: "Guide for reverse-engineering ONNX models to pure PyTorch implementations. Invoke when converting ONNX models to PyTorch, debugging architecture mismatches, or verifying PyTorch-ONNX equivalence."
---

# ONNX to PyTorch Reverse Engineering Guide

## When to Use

- Converting ONNX models to pure PyTorch
- Debugging shape/value mismatches between ONNX and PyTorch
- Extracting and mapping ONNX weights to PyTorch modules
- Understanding complex ONNX architectures

## Core Methodology

### Phase 1: ONNX Model Exploration

**Extract intermediate node outputs:**
```python
import onnx
import onnxruntime as ort
import copy

model = onnx.load('model.onnx')
model_tmp = copy.deepcopy(model)
model_tmp.graph.output.clear()

# Add target node as output
new_output = onnx.ValueInfoProto()
new_output.name = '/path/to/node_output'
model_tmp.graph.output.append(new_output)

onnx.save(model_tmp, '/tmp/extract.onnx')
session = ort.InferenceSession('/tmp/extract.onnx')
output = session.run(None, inputs)[0]
```

**Key inspection techniques:**
- Iterate all nodes: `for node in model.graph.node`
- Check initializers (weights): `for init in model.graph.initializer`
- Find nodes by pattern: `if 'pattern' in node.name`
- Trace data flow: examine `node.input` and `node.output`

### Phase 2: Architecture Derivation

**Identify module boundaries:**
- Look for naming conventions in node names (numbered modules, hierarchical prefixes)
- Group related nodes by prefix patterns
- Identify skip connections (Add nodes receiving inputs from different layers)
- Find parallel branches (same input → multiple paths → merged)
- Trace the main data flow from input to output

**Common ONNX patterns to recognize:**
- `Conv + Normalization + Activation` → ConvBlock
- `Gemm` (after Flatten/Reshape) → Linear layer
- `Add` with same-shape tensors → residual connection or branch merge
- `Concat` → feature fusion from multiple sources
- `Resize` with scale_factor → upsampling/downsampling
- `Mul` with constant → scaling (check value to infer intent: 0.5 = average, 0.707 = 1/√2)
- `Split` followed by separate processing → parallel branches

### Phase 3: Weight Loading

**Basic weight extraction:**
```python
import onnx
import torch

weights = {}
for init in model.graph.initializer:
    arr = onnx.numpy_helper.to_array(init)
    weights[init.name] = torch.from_numpy(arr.copy()).float()
```

**Common transformations:**
- `MatMul` weight → PyTorch Linear: often needs `.T` (transpose)
- `Conv` weight → PyTorch Conv: usually same shape
- `Gemm` weight → depends on `transB` attribute

**Name mapping strategy:**
```python
def map_weight_name(onnx_name, prefix_map):
    pytorch_name = onnx_name
    for old_prefix, new_prefix in prefix_map.items():
        pytorch_name = pytorch_name.replace(old_prefix, new_prefix)
    return pytorch_name
```

**Special parameters to identify:**
- Constants used as scaling factors (look for `Constant` nodes with single values)
- Normalization parameters (weight/bias presence determines `affine` setting)
- Learned parameters vs fixed constants (in initializers vs in node attributes)

### Phase 4: Implementation

**Critical details to verify from ONNX:**

#### Activation Function Parameters
- Always check slope/threshold values in node attributes
- Never assume defaults (LeakyReLU slope varies: 0.01, 0.1, 0.2)

#### Normalization Layers
- Check if weight/bias exist in initializers → determines `affine` parameter
- Verify epsilon value in node attributes
- Understand the difference between batch vs instance vs layer normalization

#### Adaptive Normalization (AdaIN/Conditional Norm)
- Common pattern: style vector → FC layer → split into scale/shift → apply to normalized input
- Watch for `(scale + constant) * normalized + shift` patterns
- The constant added to scale varies (often 1.0, but verify)

#### Upsampling Operations
- ConvTranspose may need `output_padding` for exact size matching
- Verify: `output_size = (input - 1) * stride - 2 * padding + kernel + output_padding`
- Resize with mode='nearest' → `F.interpolate(mode='nearest')`

#### Parallel Branch Merging
- Multiple branches → Add → check if followed by Mul/Div with constant
- Common pattern: `(branch1 + branch2) / num_branches`
- Verify the division constant from ONNX graph

#### Tensor Slicing
- Check `starts`, `ends`, `axes` attributes carefully
- Boundary trimming is common after certain operations (conv, transposed conv)
- Negative indices in slicing need careful handling

### Phase 5: Verification Strategy

**Layer-by-layer verification:**
```python
def verify_module(pt_output, onnx_output, name="module"):
    max_diff = torch.abs(pt_output - onnx_output).max()
    mean_diff = torch.abs(pt_output - onnx_output).mean()
    corr = np.corrcoef(
        pt_output.flatten().numpy(), 
        onnx_output.flatten()
    )[0, 1]
    
    print(f"{name}:")
    print(f"  Shape match: {pt_output.shape == onnx_output.shape}")
    print(f"  Max diff: {max_diff:.8e}")
    print(f"  Correlation: {corr:.6f}")
    
    assert max_diff < 1e-4, f"Max diff too large: {max_diff}"
    assert corr > 0.99, f"Correlation too low: {corr}"
```

**Verification order (bottom-up):**
1. Individual layers (Conv, Linear, Norm)
2. Small building blocks
3. Medium modules
4. Large modules
5. End-to-end output

**Common failures and root causes:**

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Channel shape mismatch | Wrong slicing or weight transpose | Check dimension indexing, transpose weights |
| Spatial/temporal shape mismatch | Padding or upsampling issue | Verify padding values, check output_padding |
| Max diff ~1e-3 to 1e-2 | Precision or normalization eps | Check eps values, ensure .float() |
| Max diff > 0.1 | Architectural error | Re-examine graph structure |
| Correlation < 0.95 | Wrong module connections | Verify data flow, skip connections |

### Phase 6: Debugging Workflow

**Shape debugging process:**
1. Print shapes at each step in both ONNX and PyTorch
2. Find the first point where shapes diverge
3. Work backwards to identify root cause
4. Check weight shapes, input shapes, operation semantics

**Value debugging process:**
1. Start from first layer where values diverge
2. Compare inputs to that layer (should match if previous layers are correct)
3. Compare weights of that layer
4. Compare operation parameters (stride, padding, eps, etc.)

**Common pitfalls:**
- Slicing wrong dimension: `tensor[:ch]` vs `tensor[:, :ch]`
- Assuming default parameters instead of reading from ONNX
- Missing learnable parameters in normalization layers
- Incorrect weight transposition for Linear layers
- Forgetting output_padding in ConvTranspose layers

## Best Practices

1. **Verify incrementally**: One layer at a time, don't skip ahead
2. **Save ONNX intermediates**: Keep outputs for comparison throughout development
3. **Name modules systematically**: Match PyTorch names to ONNX naming patterns
4. **Document assumptions**: Note inferred parameters and verify them
5. **Test with multiple inputs**: Catch edge cases and ensure robustness
6. **Keep verification scripts**: Reuse for debugging and future projects
7. **Understand before implementing**: Fully trace the graph before writing code

## Quick Reference: ONNX Ops

| ONNX Op | PyTorch Equivalent | Notes |
|---------|-------------------|-------|
| Conv | nn.Conv1d/2d | Check groups, padding, dilation |
| ConvTranspose | nn.ConvTranspose1d | May need output_padding |
| Gemm | nn.Linear | Check transB attribute |
| MatMul | @ or torch.matmul | May need weight transpose |
| InstanceNormalization | nn.InstanceNorm1d | Check affine from initializers |
| LayerNormalization | F.layer_norm | Specify normalized_shape |
| LeakyRelu | F.leaky_relu(x, slope) | Read slope from attributes |
| Relu | F.relu | - |
| Add | + | Check broadcasting rules |
| Mul | * | Check broadcasting rules |
| Concat | torch.cat | Check dimension |
| Resize | F.interpolate | Check mode and scale factors |
| Slice | tensor indexing | Check axes, starts, ends |
| Reshape | tensor.view()/reshape() | - |
| Transpose | tensor.transpose()/permute() | - |
| Split | torch.chunk/split | Check num_outputs |
