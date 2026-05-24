#! /usr/bin/env python
# coding=utf-8

# /************************************************************************************
# ***
# ***    File Author: Dell, 2018年 09月 21日 星期五 10:25:44 CST
# ***
# ************************************************************************************/
#

import os
import sys
import argparse
import torch
import model
import data
from config import Config
parser = argparse.ArgumentParser(description='Evaluate Text CNN classificer')
torch.serialization.add_safe_globals([model.TextCNN])
parser.add_argument(
    '-model',
    type=str,
    default="model/textcnn.model",
    help='filename of pre-trained model [model/textcnn.model]')

if __name__ == '__main__':
    conf = Config()
    args = parser.parse_args()

    print("Loading data...")
    test_iter, text_field, label_field = data.fasttext_dataloader(
        "data/test.txt", conf.batch_size, shuffle=False)

    # model
    if os.path.exists(args.model):
        print('Loading model from {}...'.format(args.model))
        cnn = torch.load(args.model, weights_only=False)
    else:
        print("Model doesn't exist.")
        sys.exit(-1)

    text_field.vocab = data.load_vocab("model/text.vocab")
    label_field.vocab = data.load_vocab("model/label.vocab")

    print(cnn)

    try:
        accuracy = model.eval(test_iter, cnn, conf)
        print(f"Evaluation completed with accuracy: {accuracy:.4f}%")
    except Exception as e:
        print(f"Evaluation failed: {str(e)}")
        print("Please check if the test dataset exists and is properly formatted.")
