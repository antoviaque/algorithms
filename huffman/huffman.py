#!/usr/bin/python
# -*- coding: utf-8 -*-

from bitstring import BitArray
import json, codecs, sys

# Functions #####################################

def get_tree(text):
    frequency = {}
    for c in text:
        if c not in frequency:
            frequency[c] = 1
        else:
            frequency[c] += 1

    tree = [ [[key], freq, []] for (key,freq) in frequency.iteritems() ]
    while len(tree) > 1:
        low1 = None
        low2 = None
        i = 0
        for keys, freq, children in tree:
            if low1 is None or low1[1]>freq:
                low1 = [i, freq]
            elif low2 is None or low2[1]>freq:
                low2 = [i, freq]
            i += 1
        
        if low1 > low2:
            tmp = low1
            low1 = low2
            low2 = low1
        low2 = tree.pop(low2[0])
        low1 = tree.pop(low1[0])

        low = [ low1[0]+low2[0], low1[1]+low2[1], [low2, low1] ]
        tree.append(low)

    print tree
    return tree

def get_code(char, tree, code=""):
    if len(tree) != 1:
        raise KeyError
    keys, freq, children = tree[0]

    if len(children) == 0:
        return code
    
    if char in children[0][0]:
        code += "0"
        return get_code(char, [children[0]], code=code)
    elif char in children[1][0]:
        code += "1"
        return get_code(char, [children[1]], code=code)
    else:
        raise KeyError

def get_decompression_tree(tree):
    if len(tree) != 1:
        raise KeyError
    keys, freq, children = tree[0]

    if len(children) == 0:
        if len(keys) != 1:
            raise KeyError
        return keys[0]
    elif len(children) == 2:
        return [get_decompression_tree([children[0]]),
                get_decompression_tree([children[1]])]
    else:
        raise KeyError

def get_char(code, tree, index):
    if len(tree) == 1:
        char = tree
        return tree, code, index

    branch = code[index]
    index += 1

    if branch == '0':
        return get_char(code, tree[0], index)
    elif branch == '1':
        return get_char(code, tree[1], index)
    else:
        raise KeyError

def compress(text):
    tree = get_tree(text)
    decompression_tree = get_decompression_tree(tree)

    compressed_text = ""
    for c in text:
        compressed_text += get_code(c, tree)
    # Add filler to get to a round nb of bytes
    compressed_text += '0' * (8 - (len(compressed_text) % 8)) 

    binary = BitArray()
    binary.bin = compressed_text

    return binary, decompression_tree

def tree2json(tree):
    return json.dumps(tree, ensure_ascii=False).replace('" "', 'XXX').replace(' ', '').replace('XXX', '" "')

def decompress(data, tree):
    binary = BitArray()
    binary.bytes = data
    binary = binary.bin

    text = []
    index = 0
    while True:
        try:
            c, binary, index = get_char(binary, tree, index)
        except IndexError:
            break
        text.append(c)

    return "".join(text)

# Main ##################################

filename = 'book.txt'

# Compression

with open(filename, 'r') as f:
    text = f.read()

data, tree = compress(text)

with open("%s.huffman" % filename, 'w+') as f:
    f.write(data.bytes)

with open("%s.huffman_tree" % filename, 'w+') as f:
    f.write(tree2json(tree))

# Decompression

with open("%s.huffman" % filename) as f:
    data = f.read()

with open("%s.huffman_tree" % filename, 'r') as f:
    tree = json.loads(f.read())

text = decompress(data, tree)

with codecs.open("%s.uncompressed" % filename, 'w+', 'utf-8') as f:
    f.write(text)


