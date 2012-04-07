#!/usr/bin/python
# -*- coding: utf-8 -*-

from bitstring import BitArray, BitStream
import json, codecs, sys, math

WINDOW_BITS = 12

# Functions #####################################

def text2feed(text):
    feed = []
    cache = []
    max_length = 1
    pos = 0
    text_length = len(text)
    while pos < text_length:
        ahead = pos + max_length
        if ahead > text_length:
            ahead = text_length
        word = ''
        while ahead > pos:
            if text[pos:ahead] in cache:
                word = text[pos:ahead]
                break
            ahead -= 1

        new_pos = pos + len(word) + 1
        if new_pos > text_length:
            new_pos = text_length
        new_word = text[pos:new_pos]

        feed_pos = 0
        if word in cache:
            feed_pos = cache.index(word) + 1
        feed.append([ feed_pos,
                      text[new_pos-1:new_pos] ])
        cache.insert(0, new_word)
        if len(cache) >= math.pow(2, WINDOW_BITS) - 1:
            cache.pop()

        pos = new_pos
        if len(new_word) > max_length:
            max_length = len(new_word)

    return feed

def fixed_length_bin(number, length):
    return ('0b{0:0%db}' % length).format(number)

def padding_bits(binary_str):
    if len(binary_str) % 8:
        return '0b' + '0' * (8 - (len(binary_str) % 8))
    else:
        return ''

def compress(text):
    feed = text2feed(text)
    binary = BitArray()
    for feed_pos, c in feed:
        binary += fixed_length_bin(feed_pos, WINDOW_BITS)
        binary += fixed_length_bin(ord(c), 8)
    binary += padding_bits(binary.bin)

    return binary.bytes

def feed2text(feed):
    text = []
    feed_pos = 0
    for rel_pos, c in feed:
        cur_text = c
        sub_pos = feed_pos
        while rel_pos:
            sub_pos -= rel_pos
            rel_pos, c = feed[sub_pos]
            cur_text = c + cur_text
        text.append(cur_text)
        feed_pos += 1
        #sys.stdout.write(cur_text+'|')

    return "".join(text)

def decompress(data):
    feed = []
    pos = 0
    binary = BitStream(bytes=data)
    binary_length = len(binary.bin)
    while binary_length - binary.pos >= 8:
        feed_pos = binary.read('uint:%d' % WINDOW_BITS)
        c = binary.read('bytes:1')
        feed.append([feed_pos, c])

    return feed2text(feed)

# Main ##################################

filename = 'book.txt'

# Compression

with open(filename, 'r') as f:
    text = f.read()

data = compress(text)

with open("%s.lz" % filename, 'w+') as f:
    f.write(data)

# Decompression

with open("%s.lz" % filename) as f:
    data = f.read()

text = decompress(data)

with open("%s.uncompressed" % filename, 'w+') as f:
    f.write(text)



