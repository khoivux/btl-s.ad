import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
# import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import os

class UserBehaviorDataset(Dataset):
    def __init__(self, sequences, targets):
        self.sequences = torch.tensor(sequences, dtype=torch.long)
        self.targets = torch.tensor(targets, dtype=torch.long)
        
    def __len__(self):
        return len(self.sequences)
        
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]

def prepare_data(csv_path, seq_length=10):
    df = pd.read_csv(csv_path)
    
    max_prod = int(df['product_id'].max()) + 1
    df['product_id'] = df['product_id'].astype(int) - 1
    
    action_map = {
        'view': 1, 'click': 2, 'add_to_cart': 3, 'remove_from_cart': 4, 
        'purchase': 5, 'wishlist': 6, 'review': 7, 'share': 8
    }
    df['action'] = df['action'].map(action_map).fillna(0).astype(int)
    
    sequences = []
    targets = []
    
    for user_id, group in df.groupby('user_id'):
        user_prods = group['product_id'].values
        user_actions = group['action'].values
        
        if len(user_prods) <= seq_length: continue
        
        for i in range(len(user_prods) - seq_length):
            seq_p = user_prods[i:i+seq_length]
            seq_a = user_actions[i:i+seq_length]
            seq = np.stack([seq_p, seq_a], axis=1) # shape: (seq_length, 2)
            target = user_prods[i+seq_length]
            
            sequences.append(seq)
            targets.append(target)
            
    return np.array(sequences), np.array(targets), max_prod, len(action_map) + 1

class SequenceRecommender(nn.Module):
    def __init__(self, num_products, num_actions, model_type='LSTM', hidden_dim=128, num_layers=2):
        super(SequenceRecommender, self).__init__()
        self.model_type = model_type
        
        self.prod_emb = nn.Embedding(num_products + 1, 64)
        self.act_emb = nn.Embedding(num_actions, 16)
        
        input_dim = 64 + 16
        self.is_bidirectional = (model_type == 'biLSTM')
        rnn_kwargs = {
            'input_size': input_dim, 
            'hidden_size': hidden_dim, 
            'num_layers': num_layers, 
            'batch_first': True,
            'dropout': 0.2 if num_layers > 1 else 0
        }
        
        if model_type == 'RNN':
            self.rnn = nn.RNN(**rnn_kwargs)
        elif model_type == 'LSTM':
            self.rnn = nn.LSTM(**rnn_kwargs)
        elif model_type == 'biLSTM':
            rnn_kwargs['bidirectional'] = True
            self.rnn = nn.LSTM(**rnn_kwargs)
            
        rnn_out_dim = hidden_dim * 2 if self.is_bidirectional else hidden_dim
        self.fc = nn.Sequential(
            nn.Linear(rnn_out_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_products)
        )
        
    def forward(self, x):
        p_seq = x[:, :, 0]
        a_seq = x[:, :, 1]
        
        p_emb = self.prod_emb(p_seq)
        a_emb = self.act_emb(a_seq)
        
        rnn_in = torch.cat([p_emb, a_emb], dim=-1)
        
        out, _ = self.rnn(rnn_in)
        last_out = out[:, -1, :]
        logits = self.fc(last_out)
        return logits

def evaluate_model(model, iter_val, criterion, device="cpu"):
    model.eval()
    val_loss = 0
    all_preds, all_targs = [], []
    with torch.no_grad():
        for seqs, targets in iter_val:
            seqs, targets = seqs.to(device), targets.to(device)
            out = model(seqs)
            loss = criterion(out, targets)
            val_loss += loss.item() * seqs.size(0)
            
            preds = torch.argmax(out, dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_targs.extend(targets.cpu().numpy())
            
    avg_loss = val_loss / len(all_preds)
    acc = accuracy_score(all_targs, all_preds)
    prec = precision_score(all_targs, all_preds, average='macro', zero_division=0)
    rec = recall_score(all_targs, all_preds, average='macro', zero_division=0)
    f1 = f1_score(all_targs, all_preds, average='macro', zero_division=0)
    
    return avg_loss, acc, prec, rec, f1

def train_and_evaluate():
    data_path = '../../data_user500.csv'
    if not os.path.exists(data_path):
        data_path = 'data_user500.csv'  # depending on execution cwd
        if not os.path.exists(data_path):
            data_path = "c:/bookstore-micro05/recommender-ai-service/data_user500.csv"
            
    print("[INFO] Preparing Data...")
    X, y, num_products, num_actions = prepare_data(data_path, seq_length=10)
    print(f"Data shape: Sequences: {X.shape}, Targets: {y.shape}")
    
    if len(X) == 0:
        print("ERROR: No data sequences. Adjust seq_length")
        return

    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)
    
    train_loader = DataLoader(UserBehaviorDataset(X_train, y_train), batch_size=256, shuffle=True)
    val_loader = DataLoader(UserBehaviorDataset(X_val, y_val), batch_size=256, shuffle=False)
    test_loader = DataLoader(UserBehaviorDataset(X_test, y_test), batch_size=256, shuffle=False)
    
    model_types = ['RNN', 'LSTM', 'biLSTM']
    results = {}
    epochs = 5

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    best_model_name = ""
    best_acc = 0
    
    for mt in model_types:
        print(f"\\n[TRAINING] Starting to train {mt} model...")
        model = SequenceRecommender(num_products, num_actions, model_type=mt).to(device)
        optimizer = optim.Adam(model.parameters(), lr=0.005)
        criterion = nn.CrossEntropyLoss()
        
        train_losses, val_losses = [], []
        
        for epoch in range(epochs):
            model.train()
            total_loss = 0
            for seqs, targets in train_loader:
                seqs, targets = seqs.to(device), targets.to(device)
                optimizer.zero_grad()
                out = model(seqs)
                loss = criterion(out, targets)
                loss.backward()
                optimizer.step()
                total_loss += loss.item() * seqs.size(0)
                
            train_loss = total_loss / len(X_train)
            v_loss, v_acc, v_prec, v_rec, v_f1 = evaluate_model(model, val_loader, criterion, device)
            
            train_losses.append(train_loss)
            val_losses.append(v_loss)
            print(f"  > {mt} Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.4f} - Val Loss: {v_loss:.4f} - Val Acc: {v_acc:.4f}")
            
        t_loss, t_acc, t_prec, t_rec, t_f1 = evaluate_model(model, test_loader, criterion, device)
        print(f"[RESULT] {mt} Test Set Evaluation -> Acc: {t_acc:.4f}, Prec: {t_prec:.4f}, Rec: {t_rec:.4f}, F1: {t_f1:.4f}")
        
        results[mt] = {
            'train_losses': train_losses,
            'val_losses': val_losses,
            'test_acc': t_acc,
            'test_f1': t_f1
        }
        
        if t_acc > best_acc:
            best_acc = t_acc
            best_model_name = mt
            try:
                os.makedirs('../ai_core', exist_ok=True)
                torch.save(model.state_dict(), '../ai_core/behavior_model_best.pth')
            except Exception as e:
                print("Could not save model to ../ai_core. Saving to current dir.")
                torch.save(model.state_dict(), 'behavior_model_best.pth')
            
    print(f"\\n[CONCLUSION] Best Model Selected: {best_model_name} with Accuracy {best_acc:.4f}")
    
    # plt.figure(figsize=(10,6))
    # for mt in model_types:
    #     plt.plot(range(1, epochs+1), results[mt]['val_losses'], label=f'{mt} (Final Val Loss: {results[mt]["val_losses"][-1]:.4f})')
        
    # plt.title('Validation Loss Comparison (RNN vs LSTM vs biLSTM)')
    # plt.xlabel('Epochs')
    # plt.ylabel('Loss (Cross Entropy)')
    # plt.legend()
    # plt.grid()
    # plt.savefig('metrics_loss_plot.png')
    # print("Metrics plot saved to 'metrics_loss_plot.png'.")

    
    with open('model_evaluation.txt', 'w', encoding='utf-8') as f:
        f.write(f"Đánh giá 3 Mô hình dự đoán hành vi người dùng\\n")
        f.write(f"============================================\\n")
        for mt in model_types:
            f.write(f"- {mt} Model -> Test Accuracy: {results[mt]['test_acc']:.4f}, F1-score: {results[mt]['test_f1']:.4f}\\n")
        f.write(f"\\nMô hình tốt nhất được chọn: {best_model_name}\\n")
        f.write("Lý do chọn: Mô hình này đạt được độ chính xác (Accuracy) cao nhất trên tập Test, cho thấy khả năng nắm bắt quan hệ chuỗi và xu hướng tuần tự trong hành vi sản phẩm tốt hơn so với các kiến trúc còn lại.\\n")

if __name__ == '__main__':
    train_and_evaluate()
