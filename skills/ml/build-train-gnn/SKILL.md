---
name: build-train-gnn
category: ml
description: >
  Build and train Graph Neural Networks with PyTorch Geometric (PyG). Use to wrap graph
  data in a Data/HeteroData object, pick a message-passing layer (GCNConv, SAGEConv,
  GATConv, GINConv), mini-batch huge graphs with NeighborLoader, or train node-
  classification, link-prediction, and graph-classification models. Covers edge_index COO
  layout, train/val/test masks, to_hetero, global pooling, and evaluation.
when_to_use:
  - Turning a graph (nodes + edges + features) into a trainable PyG Data object
  - Choosing and wiring GCN / GraphSAGE / GAT / GIN message-passing layers
  - Mini-batching a graph too large for full-batch training via NeighborLoader
  - Building a heterogeneous GNN over multiple node/edge types with to_hetero
  - Doing node classification, link prediction, or whole-graph classification
when_not_to_use:
  - Plain tabular/image/text with no relational structure — use a standard MLP/CNN/transformer instead
  - Learning backprop/autograd fundamentals by hand — use neural-net-from-scratch
  - Only scoring an already-trained model — use ml-model-eval
  - Producing dense node embeddings for retrieval without a task head — use embedding-model-training
keywords:
  - pytorch-geometric
  - pyg
  - graph-neural-network
  - gnn
  - gcn
  - graphsage
  - gat
  - gin
  - message-passing
  - neighborloader
  - heterodata
  - node-classification
  - link-prediction
  - graph-classification
  - edge-index
similar_to:
  - neural-net-from-scratch
  - lora-qlora-finetune
  - embedding-model-training
  - ml-model-eval
inputs_needed: A graph as node features (x), connectivity (edge_index in COO), optional edge/label tensors; or a built-in dataset (Planetoid, OGB, TUDataset). Python 3.9+, torch, torch_geometric.
produces: A trained torch.nn.Module GNN plus a training/eval loop, task metrics (accuracy/AUC), and saved weights.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Build & Train a Graph Neural Network (PyTorch Geometric)

Wrap a graph in PyG's `Data`, pick a message-passing layer, and train it for a node / edge /
graph task. Every snippet is runnable and grounded against the PyG docs.

## When to use

When your data is **relational** — social graphs, molecules, citation networks, knowledge
graphs, recommenders — and the connectivity carries signal. If rows are i.i.d., use a plain MLP.

## Prerequisites

- **Python 3.9+** and **PyTorch** first (PyG builds on it).
- **PyTorch Geometric** — modern wheels bundle the compiled ops:
  ```bash
  python3 -m pip install torch torch_geometric        # core; pure-python for most layers
  ```
  Optional accel/sampling extras (`pyg_lib`, `torch_scatter`, `torch_sparse`) need
  version-matched wheels from `https://data.pyg.org/whl/`. `NeighborLoader` runs without
  them (just slower). Skip extras unless you hit a sampling perf wall. No GPU needed for
  these recipes; pass `device='cuda'` if you have one. Verify first (see **Verify**).

## Core data model (read this first)

A single graph is a `Data` object. Two shape rules govern everything:

- `x`: node features, `[num_nodes, num_node_features]`, float.
- `edge_index`: connectivity in **COO**, `[2, num_edges]`, dtype `torch.long`. Row 0 =
  source ids, row 1 = destination. Directed — for an undirected edge add both `(i,j)` and `(j,i)`.
- `y`: labels (per-node, per-edge, or per-graph). `edge_attr` (optional): `[num_edges, F]`.

```python
import torch
from torch_geometric.data import Data
# 3 nodes, undirected path 0-1-2  → 4 directed edges
edge_index = torch.tensor([[0, 1, 1, 2],
                           [1, 0, 2, 1]], dtype=torch.long)
data = Data(x=torch.randn(3, 16), edge_index=edge_index, y=torch.tensor([0, 1, 0]))
data.validate(raise_on_error=True)        # catches shape/dtype mistakes early
```

Edges as a list of `(src, dst)` **rows**? Transpose:
`torch.tensor(pairs, dtype=torch.long).t().contiguous()`.

## Recipe 1 — Node classification (full-batch GCN on Cora)

The canonical semi-supervised setup: one big graph, boolean `train/val/test_mask`.

```python
import torch, torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.datasets import Planetoid

dataset = Planetoid(root='/tmp/Cora', name='Cora')   # downloads once
data = dataset[0]

class GCN(torch.nn.Module):
    def __init__(self, in_dim, hidden, out_dim):
        super().__init__()
        self.conv1 = GCNConv(in_dim, hidden)
        self.conv2 = GCNConv(hidden, out_dim)
    def forward(self, x, edge_index):
        x = F.relu(self.conv1(x, edge_index))
        x = F.dropout(x, p=0.5, training=self.training)
        return self.conv2(x, edge_index)             # raw logits

model = GCN(dataset.num_node_features, 16, dataset.num_classes)
opt = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)

@torch.no_grad()
def acc(mask):
    model.eval()
    pred = model(data.x, data.edge_index).argmax(dim=1)
    return float((pred[mask] == data.y[mask]).float().mean())

best_val = 0
for epoch in range(1, 201):
    model.train(); opt.zero_grad()
    out = model(data.x, data.edge_index)
    loss = F.cross_entropy(out[data.train_mask], data.y[data.train_mask])
    loss.backward(); opt.step()
    if acc(data.val_mask) > best_val:
        best_val = acc(data.val_mask)
        torch.save(model.state_dict(), 'gcn_cora.pt')
print('test acc', acc(data.test_mask))   # ~0.81
```

`cross_entropy` on raw logits == `nll_loss(log_softmax(...))` — don't apply softmax twice.

## Recipe 2 — Swap the layer (GraphSAGE / GAT / GIN)

Same `forward` contract as GCN; only the constructor changes. Drop-in replacements:

```python
from torch_geometric.nn import SAGEConv, GATConv, GINConv
from torch.nn import Sequential, Linear, ReLU

conv = SAGEConv(in_dim, hidden)                      # GraphSAGE — robust default, scales
conv = GATConv(in_dim, hidden, heads=8)              # GAT attention -> output dim hidden*8
conv_out = GATConv(hidden * 8, out_dim, heads=1, concat=False)   # GAT final layer
conv = GINConv(Sequential(Linear(in_dim, hidden), ReLU(), Linear(hidden, hidden)))  # GIN
```

Rule of thumb: **SAGE** for large/sampled graphs, **GAT** when edge importance varies,
**GIN** for whole-graph tasks, **GCN** as the simple baseline.

## Recipe 3 — Mini-batch a huge graph (NeighborLoader + GraphSAGE)

When the graph won't fit in memory, sample a fixed-size neighborhood per seed node each step.

```python
from torch_geometric.loader import NeighborLoader

train_loader = NeighborLoader(
    data,
    num_neighbors=[10, 10],          # 10 neighbors at hop 1, 10 at hop 2 (len == #layers)
    batch_size=128,
    input_nodes=data.train_mask,     # seed only from training nodes
    shuffle=True,
)

model = GCN(dataset.num_node_features, 64, dataset.num_classes)  # or a SAGE model
opt = torch.optim.Adam(model.parameters(), lr=0.01)

for epoch in range(1, 11):
    model.train()
    for batch in train_loader:
        opt.zero_grad()
        out = model(batch.x, batch.edge_index)
        # CRITICAL: the first `batch.batch_size` rows are the seed nodes; only they get loss
        loss = F.cross_entropy(out[:batch.batch_size],
                               batch.y[:batch.batch_size])
        loss.backward(); opt.step()
```

`num_neighbors` length **must equal the number of conv layers**; `batch.n_id` maps sampled
rows back to original ids. For exact inference, do a full-batch pass on CPU.

## Recipe 4 — Heterogeneous graph (multiple node/edge types)

Node types have different feature dims. Build a homogeneous model with **lazy** input
channels (`-1`), then let `to_hetero` replicate it per relation.

```python
from torch_geometric.data import HeteroData
from torch_geometric.nn import SAGEConv, to_hetero

data = HeteroData()
data['author'].x = torch.randn(100, 32)
data['paper'].x  = torch.randn(500, 64)
data['author', 'writes', 'paper'].edge_index = torch.randint(0, 100, (2, 800))
# add reverse relation so papers can message authors:
data['paper', 'rev_writes', 'author'].edge_index = data['author','writes','paper'].edge_index.flip(0)

class Net(torch.nn.Module):
    def __init__(self, hidden, out):
        super().__init__()
        self.conv1 = SAGEConv((-1, -1), hidden)   # (-1,-1) = infer src/dst dims lazily
        self.conv2 = SAGEConv((-1, -1), out)
    def forward(self, x, edge_index):
        x = F.relu(self.conv1(x, edge_index))
        return self.conv2(x, edge_index)

model = to_hetero(Net(64, 16), data.metadata(), aggr='sum')
out = model(data.x_dict, data.edge_index_dict)     # returns a dict keyed by node type
```

For `GATConv` in a hetero/bipartite model pass `add_self_loops=False` — self-loops are
undefined when source and destination node types differ.

## Recipe 5 — Link prediction (edge-level task head)

Encode nodes with any of the models above, score candidate pairs by dot product, train
against sampled negatives:

```python
from torch_geometric.utils import negative_sampling

z = enc(data.x, data.edge_index)                  # [N, d] node embeddings from any encoder
pos = data.edge_index                             # observed (positive) edges
neg = negative_sampling(pos, num_nodes=data.num_nodes, num_neg_samples=pos.size(1))
ei  = torch.cat([pos, neg], dim=1)
labels = torch.cat([torch.ones(pos.size(1)), torch.zeros(neg.size(1))])
logits = (z[ei[0]] * z[ei[1]]).sum(dim=-1)        # dot-product decoder
loss = F.binary_cross_entropy_with_logits(logits, labels)
```

Recompute `z`/`neg` each epoch. Use `transforms.RandomLinkSplit` for a leakage-free split and
score val/test with ROC-AUC (`sklearn.metrics.roc_auc_score`) — see ml-model-eval.

## Recipe 6 — Graph classification (graph-level task head)

Many small graphs. PyG's `DataLoader` merges a batch into one big disjoint graph plus a
`batch` vector (node → graph); `global_mean_pool` collapses each graph to one vector:

```python
from torch_geometric.datasets import TUDataset
from torch_geometric.loader import DataLoader
from torch_geometric.nn import global_mean_pool     # or global_max_pool / global_add_pool

dataset = TUDataset(root='/tmp/MUTAG', name='MUTAG').shuffle()
train_loader = DataLoader(dataset[:150], batch_size=32, shuffle=True)

class GraphNet(torch.nn.Module):
    def __init__(self, in_dim, hidden, out_dim):
        super().__init__()
        self.conv1, self.conv2 = GCNConv(in_dim, hidden), GCNConv(hidden, hidden)
        self.lin = torch.nn.Linear(hidden, out_dim)
    def forward(self, x, edge_index, batch):
        x = F.relu(self.conv1(x, edge_index))
        x = F.relu(self.conv2(x, edge_index))
        x = global_mean_pool(x, batch)               # [num_graphs, hidden]
        return self.lin(F.dropout(x, p=0.5, training=self.training))

model = GraphNet(dataset.num_node_features, 64, dataset.num_classes)
opt = torch.optim.Adam(model.parameters(), lr=0.01)
for batch in train_loader:
    opt.zero_grad()
    out = model(batch.x, batch.edge_index, batch.batch)
    F.cross_entropy(out, batch.y).backward(); opt.step()
```

`global_add_pool` pairs well with GIN for maximal expressiveness.

## Verify

```bash
python3 - <<'PY'
import torch, torch_geometric
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data
print('torch', torch.__version__, '| pyg', torch_geometric.__version__)
d = Data(x=torch.randn(3,4),
         edge_index=torch.tensor([[0,1,2],[1,2,0]]))
d.validate(raise_on_error=True)
out = GCNConv(4, 8)(d.x, d.edge_index)
assert out.shape == (3, 8), out.shape
print('OK: forward pass', tuple(out.shape))
PY
```

Prints versions and `OK: forward pass (3, 8)`. During training: loss should fall and val
accuracy track train — a large train–val gap means overfitting (raise dropout/weight_decay).

## Pitfalls

- **edge_index dtype/shape.** Must be `torch.long`, `[2, E]`. A `[E, 2]` tensor silently
  mis-indexes — call `data.validate()`. Undirected needs both `(i,j)` and `(j,i)` (or
  `torch_geometric.utils.to_undirected`).
- **Double softmax.** Return raw logits + `F.cross_entropy`; don't `log_softmax` too.
- **NeighborLoader loss.** Only the first `batch.batch_size` rows are seeds; loss over the
  whole sampled block leaks. `num_neighbors` length must equal the conv-layer count.
- **Hetero lazy init.** Build with `(-1, -1)` dims and run one forward pass to materialize
  `.parameters()` before creating the optimizer or `load_state_dict`.
- **GAT output width.** `heads=h` with default `concat=True` gives `out_channels * h`; size
  the next layer to match or set `concat=False`.
- **Isolated nodes** get zero messages under mean aggregation — GCNConv adds self-loops by
  default, SAGEConv does not.
