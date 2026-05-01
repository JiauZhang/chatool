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
- Refactoring hardcoded weight loading to standard PyTorch initialization

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
- List all weight names: `[init.name for init in model.graph.initializer]`

### Phase 2: Architecture Derivation

**Identify module boundaries:**
- Look for naming conventions in node names (numbered modules, hierarchical prefixes)
- Group related nodes by prefix patterns
- Identify skip connections (Add nodes receiving inputs from different layers)
- Find parallel branches (same input -> multiple paths -> merged)
- Trace the main data flow from input to output
- **Detect shared weights**: Check if the same initializer name appears in multiple nodes

**Common ONNX patterns to recognize:**
- `Conv + Normalization + Activation` -> ConvBlock
- `Gemm` (after Flatten/Reshape) -> Linear layer
- `Add` with same-shape tensors -> residual connection or branch merge
- `Concat` -> feature fusion from multiple sources
- `Resize` with scale_factor -> upsampling/downsampling
- `Mul` with constant -> scaling (check value to infer intent: 0.5 = average, 0.707 = 1/sqrt(2))
- `Split` followed by separate processing -> parallel branches
- `LSTM` with direction attribute -> unidirectional or bidirectional
- `Gather`/`ScatterND` -> indexing/assignment operations

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
- `MatMul` weight -> PyTorch Linear: often needs `.T` (transpose)
- `Conv` weight -> PyTorch Conv: usually same shape
- `Gemm` weight -> depends on `transB` attribute
- `LSTM` weights -> stacked [W, R, B] for each direction, shape varies by framework

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
- Normalization parameters (weight/bias presence determines `affine` parameter)
- Learned parameters vs fixed constants (in initializers vs in node attributes)
- **Shared parameters**: Same initializer used by multiple branches (e.g., F0 and N branches sharing InstanceNorm affine params)

### Phase 4: Implementation

**Critical details to verify from ONNX:**

#### Activation Function Parameters
- Always check slope/threshold values in node attributes
- Never assume defaults (LeakyReLU slope varies: 0.01, 0.1, 0.2)

#### Normalization Layers
- Check if weight/bias exist in initializers -> determines `affine` parameter
- Verify epsilon value in node attributes
- Understand the difference between batch vs instance vs layer normalization
- **Parameter naming trap**: ONNX may use `gamma`/`beta` while PyTorch uses `weight`/`bias` - map accordingly

#### Adaptive Normalization (AdaIN/Conditional Norm)
- Common pattern: style vector -> FC layer -> split into scale/shift -> apply to normalized input
- Watch for `(scale + constant) * normalized + shift` patterns
- The constant added to scale varies (often 1.0, but verify)

#### Upsampling Operations
- ConvTranspose may need `output_padding` for exact size matching
- Verify: `output_size = (input - 1) * stride - 2 * padding + kernel + output_padding`
- Resize with mode='nearest' -> `F.interpolate(mode='nearest')`
- **Custom depthwise transpose**: ONNX may implement depthwise ConvTranspose as a custom loop - verify kernel size and stride

#### Parallel Branch Merging
- Multiple branches -> Add -> check if followed by Mul/Div with constant
- Common pattern: `(branch1 + branch2) / num_branches`
- Verify the division constant from ONNX graph
- **Shared norm result**: Branches may share the same InstanceNorm output before diverging

#### Tensor Slicing
- Check `starts`, `ends`, `axes` attributes carefully
- Boundary trimming is common after certain operations (conv, transposed conv)
- Negative indices in slicing need careful handling

#### LSTM/GRU/RNN Handling

**ONNX LSTM weight format:**
- ONNX stores LSTM weights as: W (input weights), R (recurrent weights), B (biases)
- For bidirectional: weights are stacked [fwd, rev] in the same tensor
- Gate order in ONNX: iofc (input, output, forget, cell) - **NOT** the standard ifoc

**PyTorch custom LSTM implementation:**
```python
class BidirectionalLSTM(nn.Module):
    def __init__(self, input_size, hidden_size):
        super().__init__()
        self.hidden_size = hidden_size
        # ONNX format: W, R, B are stacked [fwd, rev]
        self.W_fwd = nn.Parameter(torch.empty(4 * hidden_size, input_size))
        self.R_fwd = nn.Parameter(torch.empty(4 * hidden_size, hidden_size))
        self.B_fwd = nn.Parameter(torch.empty(8 * hidden_size))  # W_bias + R_bias
        self.W_rev = nn.Parameter(torch.empty(4 * hidden_size, input_size))
        self.R_rev = nn.Parameter(torch.empty(4 * hidden_size, hidden_size))
        self.B_rev = nn.Parameter(torch.empty(8 * hidden_size))
```

**LSTM step computation (iofc gate order):**
```python
class LSTMStep:
    @staticmethod
    def forward(x_t, W, R, B, h_prev, c_prev):
        W_bias = B[:len(B)//2]
        R_bias = B[len(B)//2:]
        gates = x_t @ W.T + h_prev @ R.T + W_bias + R_bias
        hidden = R.shape[0] // 4
        i = torch.sigmoid(gates[:, 0:hidden])
        o = torch.sigmoid(gates[:, hidden:2*hidden])
        f = torch.sigmoid(gates[:, 2*hidden:3*hidden])
        c = torch.tanh(gates[:, 3*hidden:4*hidden])
        c_new = f * c_prev + i * c
        h_new = o * torch.tanh(c_new)
        return h_new, c_new
```

**Key LSTM debugging points:**
1. Verify gate order (iofc vs ifoc)
2. Check if biases are split (W_bias + R_bias) or combined
3. For bidirectional: verify reverse direction uses correct W/R/B indices
4. Check hidden state initialization (zeros vs learned)
5. Verify input shape: ONNX LSTM expects (seq_len, batch, features)

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
| LSTM output mismatch | Wrong gate order or bias split | Verify iofc order, check B split point |
| Shared branch mismatch | Missing shared parameter | Check if branches share norm weights |

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
- **Wrong LSTM direction**: Using W_fwd for both directions in bidirectional
- **Missing shared weights**: Not detecting that branches share parameters
- **Parameter name mismatch**: ONNX uses `gamma`/`beta`, PyTorch uses `weight`/`bias`

## Advanced Topics

### Shared Weights Detection

When multiple branches share parameters, the same initializer name appears in multiple nodes:

```python
# Check if the same initializer is used in multiple nodes
weight_usage = {}
initializer_names = {init.name for init in model.graph.initializer}

for node in model.graph.node:
    for input_name in node.input:
        if input_name in initializer_names:
            weight_usage.setdefault(input_name, []).append(node.name)

# Find weights used by multiple branches
for weight_name, nodes in weight_usage.items():
    if len(nodes) > 1:
        print(f"Shared weight: {weight_name} used by {len(nodes)} nodes")
```

**Common shared weight patterns:**
- Parallel prediction branches sharing normalization affine parameters
- Encoder-decoder sharing embedding weights
- Multi-task heads sharing backbone feature extractors
- Siamese networks with tied weights

**Implementation strategy:**
1. Identify which branches share which parameters
2. Create a single parameter module referenced by multiple branches
3. Or copy the parameter to each branch (if ONNX expects separate tensors)
4. Verify both branches produce identical norm outputs when given the same input

### Custom Operations

When ONNX exports custom operations or decomposes high-level ops into primitive loops:

**Detection signs:**
- Long chains of `Gather`, `ScatterND`, `Unsqueeze`, `Concat` instead of a single op
- `Loop` or `If` nodes in the graph
- Convolutions with `groups == in_channels` (depthwise) combined with manual indexing
- Multiple `Resize` + `Mul` + `Sin`/`Cos` patterns (signal processing ops)

**Reverse engineering approach:**
1. Extract the intermediate outputs to understand the overall input-output relationship
2. Identify the mathematical operation being performed (convolution, STFT, etc.)
3. Check if PyTorch has a native equivalent or if custom implementation is needed
4. Verify parameter shapes match expected operation dimensions

**Signal processing operations:**
- ONNX may implement STFT/ISTFT as Conv1d with learned or fixed complex weights
- Real and imaginary parts are often separate initializers
- Look for `Conv` + `Concat` (magnitude + phase) patterns
- Verify stride, padding, and window size match expected transform parameters

### Refactoring to Standard PyTorch Initialization

**Goal**: Convert from hardcoded weight loading in `__init__` to standard `load_state_dict`.

**Step 1: Create architecture with empty parameters**
```python
class MyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv1d(128, 128, kernel_size=5, padding=2)
        self.norm = nn.LayerNorm(128)
        # No weight loading here - just standard PyTorch initialization
```

**Step 2: Export ONNX weights to PyTorch state_dict**
```python
# Load from ONNX (temporary, for export only)
model = MyModel()
# ... load ONNX weights into model ...

# Export to .pt file
torch.save({
    'state_dict': model.state_dict(),
    'version': '1.0.0',
}, 'model_weights.pt')
```

**Step 3: Load via standard PyTorch API**
```python
model = MyModel()
checkpoint = torch.load('model_weights.pt')
model.load_state_dict(checkpoint['state_dict'], strict=True)
```

**Key mapping rules for state_dict keys:**
- Remove framework-specific prefixes (e.g., model-specific prefixes, `onnx::`)
- Replace module index notation: `layer.N.` -> `layerN.` or `layer[N].`
- Map normalization names: `gamma` -> `weight`, `beta` -> `bias`, `moving_mean` -> `running_mean`
- Handle MatMul/Gemm weights: transpose if needed for Linear layers
- Map custom op weights to standard PyTorch module equivalents

**Handling optional parameters:**
Some branches may have optional affine parameters. Use conditional loading:
```python
# In ONNX loading code
if weights.has(f'{prefix}.norm.weight'):
    module.norm.weight.data = weights.get(f'{prefix}.norm.weight')
    module.norm.bias.data = weights.get(f'{prefix}.norm.bias')
```

**Common key mapping patterns:**

| ONNX Pattern | PyTorch Pattern | Rule |
|-------------|-----------------|------|
| `model.layer.0.weight` | `layer0.weight` | Remove parent prefix, flatten index |
| `model.layer.0.1.weight` | `layer0[1].weight` | Convert to sequential index |
| `norm.gamma` | `norm.weight` | Map normalization param names |
| `norm.beta` | `norm.bias` | Map normalization param names |
| `onnx::MatMul_N` | `linear.weight` | Map by position, transpose |
| `embedding.weight` | `embedding.weight` | Often direct mapping |
| `conv.weight` | `conv.weight` | Often direct mapping |

**Automated mapping approach:**
```python
import re

def auto_map_key(onnx_name, prefix_replacements=None):
    """Automatically map ONNX weight name to PyTorch state_dict key."""
    pytorch_name = onnx_name
    
    # Apply custom prefix replacements
    if prefix_replacements:
        for old, new in prefix_replacements.items():
            pytorch_name = pytorch_name.replace(old, new)
    
    # Normalize index notation: layer.0. -> layer0.
    pytorch_name = re.sub(r'\.(\d+)\.', r'\1.', pytorch_name)
    
    # Map normalization params
    pytorch_name = pytorch_name.replace('.gamma', '.weight')
    pytorch_name = pytorch_name.replace('.beta', '.bias')
    pytorch_name = pytorch_name.replace('.moving_mean', '.running_mean')
    pytorch_name = pytorch_name.replace('.moving_var', '.running_var')
    
    return pytorch_name
```

## Best Practices

1. **Verify incrementally**: One layer at a time, don't skip ahead
2. **Save ONNX intermediates**: Keep outputs for comparison throughout development
3. **Name modules systematically**: Match PyTorch names to ONNX naming patterns
4. **Document assumptions**: Note inferred parameters and verify them
5. **Test with multiple inputs**: Catch edge cases and ensure robustness
6. **Keep verification scripts**: Reuse for debugging and future projects
7. **Understand before implementing**: Fully trace the graph before writing code
8. **Export weights early**: Once verified, export to .pt for faster loading
9. **Refactor to standard init**: Final step - make model loadable via load_state_dict
10. **Check for shared weights**: Always verify if branches share parameters

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
| LSTM | nn.LSTM or custom | Check direction, gate order |
| Gather | tensor indexing | Check axis |
| ScatterND | tensor assignment | Check indices shape |
| CumSum | torch.cumsum | Check axis |
| ReduceMean | tensor.mean() | Check axes, keepdims |
| ReduceStd | tensor.std() | Check unbiased parameter |
