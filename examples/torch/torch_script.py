import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

def main(detach=False):
    X = torch.randn(10000, 20)     
    y = torch.randint(0, 2, (10000,))
    dataset = TensorDataset(X, y)
    dataloader = DataLoader(dataset, batch_size=32)
    model = nn.Sequential(
        nn.Linear(20, 50),
        nn.ReLU(),
        nn.Linear(50, 2)
    )
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    outputs_list = []
    losses_list = []
    for epoch in range(2):
        for inputs, labels in dataloader:
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            if detach:
                outputs = outputs.detach()
                loss = loss.detach()
            outputs_list.append(outputs)
            losses_list.append(loss)
