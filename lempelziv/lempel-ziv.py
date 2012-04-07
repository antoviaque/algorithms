#!/usr/bin/python
# -*- coding: utf-8 -*-

from bitstring import BitArray, BitStream
import json, codecs, sys, math

# Globals #######################################

LENGTH_BITS = 8
WINDOW_BITS = 16

LENGTH_SIZE = int(math.pow(2, LENGTH_BITS))
WINDOW_SIZE = int(math.pow(2, WINDOW_BITS))

# Functions #####################################

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
        try:
            c = ord(c)
        except TypeError:
            pass
        binary += fixed_length_bin(c, 8)
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

#filename = 'book.txt'
filename = 'access.log'

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



