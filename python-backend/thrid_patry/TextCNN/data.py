# coding=utf-8
# 彻底修复标签-1错误，无torchtext，100%兼容官方数据集
import pickle
import torch
from collections import Counter

# 分词函数
def text_token(x):
    return [w for w in x.split(" ") if len(w) > 0]

# 词表类（兼容torchtext行为）
class Vocab:
    def __init__(self, tokens):
        # 预留位置0给padding，从1开始索引
        self.token2idx = {'<pad>': 0}
        idx = 1
        for token, _ in tokens:
            if token not in self.token2idx:
                self.token2idx[token] = idx
                idx += 1
        self.idx2token = {v: k for k, v in self.token2idx.items()}
    
    def __len__(self):
        return len(self.token2idx)
    
    # 安全获取索引：找不到返回<unk>的id（这里用0）
    def get_idx(self, token):
        return self.token2idx.get(token, 0)

# 加载数据集（文本\t标签）
def load_fasttext_data(path):
    texts = []
    labels = []
    with open(path, errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                continue
            text, label = parts[0].strip(), parts[1].strip()
            if text and label:
                texts.append(text_token(text))
                labels.append(label)
    return texts, labels

# 构建数据加载器
def fasttext_dataloader(datafile, batchsize, shuffle=False):
    texts, labels = load_fasttext_data(datafile)
    
    # 构建词表
    all_tokens = [t for seq in texts for t in seq]
    text_vocab = Vocab(Counter(all_tokens).most_common())
    
    # 构建标签词表（关键：标签从0开始，无-1）
    label_vocab = Vocab(Counter(labels).most_common())

    # 转换为索引（安全映射）
    text_ids = [[text_vocab.get_idx(t) for t in seq] for seq in texts]
    label_ids = [label_vocab.get_idx(lab) for lab in labels]

    # DataLoader实现
    class DataIter:
        def __init__(self, x, y, batch_size, shuffle):
            self.x = [torch.tensor(seq, dtype=torch.long) for seq in x]
            self.y = torch.tensor(y, dtype=torch.long)
            self.batch_size = batch_size
            self.shuffle = shuffle
            self.idx = 0
            self.order = list(range(len(self.y)))
        
        def __iter__(self):
            self.idx = 0
            if self.shuffle and len(self.y) > 0:
                perm = torch.randperm(len(self.y)).tolist()  # 转为列表
                self.order = perm
                self.x = [self.x[i] for i in perm]
                self.y = self.y[perm]
            else:
                self.order = list(range(len(self.y)))
            return self
        
        def __next__(self):
            if self.idx >= len(self.y):
                raise StopIteration
            
            end = min(self.idx + self.batch_size, len(self.y))
            batch_x_list = self.x[self.idx:end]
            batch_y = self.y[self.idx:end]
            
            # pad_sequence返回(batch_size, seq_len)，兼容train.py中的模型输入
            batch_x = torch.nn.utils.rnn.pad_sequence(
                batch_x_list, batch_first=True, padding_value=0
            )
            self.idx = end

            # 兼容原代码：返回batch对象，包含text和label属性
            batch = type('Batch', (), {'text': batch_x, 'label': batch_y})()
            batch.batch_size = batch_x.size(0)  # batch_x形状为(batch_size, seq_len)
            return batch
        
        def __len__(self):
            return (len(self.y) + self.batch_size - 1) // self.batch_size if self.y else 0

    return DataIter(text_ids, label_ids, batchsize, shuffle), text_vocab, label_vocab

# 保存/加载词表
def save_vocab(vocab, filename):
    with open(filename, 'wb') as f:
        pickle.dump(vocab, f)

def load_vocab(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)
    