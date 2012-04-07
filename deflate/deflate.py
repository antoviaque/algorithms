#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Structure:
# - 64 bits:                                Size of huffman tree structure (struct_size)
# - <struct_size> bits:                     Structure of human tree (0 = leaf, 1 = two children)
# - <struct_size> * DISTANCE_BITS bits:     Data of huffman tree (<distance> from [distance,length] backreference keypairs)
# - Until EOF):                             [<distance>,<length] LZ keypairs, or [0,<char>] for raw characters
#       - <distance_key> (variable bits):   Key of <distance>/0 in huffman tree
#       - LENGTH_BITS bits:                 Length of reference, or character

from bitstring import BitArray, BitStream
import json, codecs, sys, math

# Globals #######################################

LENGTH_BITS = 8
WINDOW_BITS = 16

LENGTH_SIZE = int(math.pow(2, LENGTH_BITS))
WINDOW_SIZE = int(math.pow(2, WINDOW_BITS))

# Functions #####################################

## General

def fixed_length_bin(number, length):
    return ('0b{0:0%db}' % length).format(number)

def padding_bits(binary_str):
    if len(binary_str) % 8:
        return '0b' + '0' * (8 - (len(binary_str) % 8))
    else:
        return ''

## LZ

def find_backreference(text, pos):
    found_len = 0
    distance = 0
    text_length = len(text)
    
    if pos < WINDOW_SIZE:
        start_pos = 0
    else:
        start_pos = pos - WINDOW_SIZE

    if pos+LENGTH_SIZE > len(text):
        end_pos = len(text)
    else:
        end_pos = pos + LENGTH_SIZE
    
    while pos+found_len+1 <= end_pos:
        search = text[pos:pos+found_len+1]
        found_pos = text.find(search, start_pos, pos)
        if found_pos == -1:
            break
        found_len = len(search)
        distance = pos - found_pos

    return [distance, found_len]

def text2feed(text):
    feed = []
    pos = 0
    text_length = len(text)
    while pos < text_length:
        distance, length = find_backreference(text, pos)
        if not distance:
            feed.append([0, text[pos:pos+1]])
            pos += 1
        else:
            feed.append([distance, length])
            pos += length

    return feed

def feed2text(feed):
    text = ""
    pos = 0
    for distance, c_or_length in feed:
        if distance == 0:
            cur_text = c_or_length
            pos += 1
        else:
            start_pos = pos - distance
            cur_text = text[start_pos:start_pos+c_or_length]
            pos += c_or_length
        text += cur_text
        #sys.stdout.write(cur_text+'|')

    return text


## Huffman

def feed2tree(feed):
    frequency = {}
    for distance, c in feed:
        if distance not in frequency:
            frequency[distance] = 1
        else:
            frequency[distance] += 1

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

    return tree

def distance2code(distance, tree, code=""):
    if len(tree) != 1:
        raise KeyError
    keys, freq, children = tree[0]

    if len(children) == 0:
        return code
    
    if distance in children[0][0]:
        code += "0"
        return distance2code(distance, [children[0]], code=code)
    elif distance in children[1][0]:
        code += "1"
        return distance2code(distance, [children[1]], code=code)
    else:
        raise KeyError

def tree2deflatetree(tree):
    if len(tree) != 1:
        raise KeyError
    keys, freq, children = tree[0]

    if len(children) == 0:
        if len(keys) != 1:
            raise KeyError
        return keys[0]
    elif len(children) == 2:
        return [tree2deflatetree([children[0]]),
                tree2deflatetree([children[1]])]
    else:
        raise KeyError


## Deflate

def flattendeflatetree(tree):
    try:
        tree_length = len(tree)
    except TypeError:
        tree_length = 1

    if tree_length == 1:
        return "0", [tree]
    elif len(tree) == 2:
        struct_left, data_left = flattendeflatetree(tree[0])
        struct_right, data_right = flattendeflatetree(tree[1])
        
        struct = "1" + struct_left + struct_right
        data = data_left + data_right
        return struct, data 
    else:
        raise KeyError

def deflatetree2bin(tree):
    struct, data = flattendeflatetree(tree)
    binary = BitArray() + fixed_length_bin(len(struct), 64)
    binary += '0b' + struct
    for distance in data:
        binary += fixed_length_bin(distance, WINDOW_BITS)
    return binary

def feed2bin(feed, tree):
    binary = BitArray()
    for distance, c in feed:
        distance_code = distance2code(distance, tree)
        binary += "0b" + distance_code
        try:
            c = ord(c)
        except TypeError:
            pass
        binary += fixed_length_bin(c, LENGTH_BITS)

    return binary

def deflate(text):
    print "1-text=",text
    feed = text2feed(text)
    print "1-feed=",feed
    tree = feed2tree(feed)
    deflate_tree = tree2deflatetree(tree)
    print "1-tree=",deflate_tree

    binary = deflatetree2bin(deflate_tree)
    binary += feed2bin(feed, tree)
    binary += padding_bits(binary.bin)

    return binary.bytes


## Inflate

def unflatten_tree(binary, struct):
    cur_struct = struct[0]
    remaining_struct = struct[1:]
    if cur_struct == '0':
        return binary.read('uint:%d' % WINDOW_BITS), remaining_struct
    elif cur_struct == '1':
        tree_left, remaining_struct = unflatten_tree(binary, remaining_struct)
        tree_right, remaining_struct = unflatten_tree(binary, remaining_struct)
        return [tree_left, tree_right], remaining_struct
    else:
        raise KeyError

def bin2deflatetree(binary):
    struct_size = binary.read('uint:64')
    struct = binary.read('bin:%d' % struct_size)
    tree, struct = unflatten_tree(binary, struct)
    return tree

def read_distance(binary, tree):
    try:
        tree_length = len(tree)
    except TypeError:
        distance = tree
        return distance

    branch = binary.read('bin:1')

    if branch == '0':
        return read_distance(binary, tree[0])
    elif branch == '1':
        return read_distance(binary, tree[1])

def bin2feed(binary, tree):
    feed = []
    binary_length = len(binary.bin)
    while binary_length - binary.pos > LENGTH_BITS:
        distance = read_distance(binary, tree)
        c_or_length = binary.read('uint:%d' % LENGTH_BITS)
        if distance == 0:
            c_or_length = chr(c_or_length)
        feed.append([distance, c_or_length])

    return feed

def inflate(data):
    binary = BitStream(bytes=data)
    tree = bin2deflatetree(binary)
    print "2-tree=", tree
    feed = bin2feed(binary, tree)
    print "2-feed=",feed
    text = feed2text(feed)
    print "2-text=",text
    return text


# Main ##################################

filename = 'test.txt'

# Compression

with open(filename, 'r') as f:
    text = f.read()[:-1]

data = deflate(text)

with open("%s.z" % filename, 'w+') as f:
    f.write(data)

# Decompression

with open("%s.z" % filename) as f:
    data = f.read()

text = inflate(data)

with open("%s.uncompressed" % filename, 'w+') as f:
    f.write(text)



