#!/usr/bin/env python

"""
    This is to convert bitmap fonts outputted by http://www.pentacom.jp/pentacom/bitfontmaker2/ as .JSON
    into C++ code compatible with Font8 class of a21 library.
"""

import json
import re
import sys
import os

min_code = 32
max_code = 127

"""
json_path = "ATARISTOCRAT.json"
offset_left = 2
offset_bottom = 3
"""
"""
json_path = "BetterPixels.json"
offset_left = 3
offset_bottom = 4
"""

"""
json_path = "BitmapMiddleFont.json"
offset_left = 2
offset_bottom = 3
"""

"""
json_path = "BitmapSmallFont.json"
offset_left = 2
offset_bottom = 3
"""

# TODO: add command line options

json_path = "PixelstadTweaked.json"
offset_left = 3
offset_bottom = 3
uppercase_only = True

show_bitmaps = True

font_data = json.load(file(json_path))

font_name = os.path.splitext(os.path.basename(json_path))[0]

"""
This gets an array of 16 bit integers each representing a horizontal line in a 16 by 16 pixels bitmap 
(each line begins with the least significant bit). The result will be an array of strings 16 characters each
corresponding to a single horizontal line with '#' or '.' characters representing each pixel.
"""
def simple_bitmap(bitmap):
	result = []
	for b in bitmap:
		s = ""
		for i in range(0, 16):
			if (b >> i) & 1 == 1:
				s += "#"
			else:
				s += "."
		result.append(s)
	return result

"""
This is not used directly, but is handy for debugging. It will return a simple bitmap as defined above
with last offset_bottom rows removed and first offset_left columns cropped.
"""
def cropped_simple_bitmap(bitmap, offset_left, offset_bottom):
	result = []
	first_row = max(0, len(bitmap) - offset_bottom - 8)
	for row in range(first_row, len(bitmap) - offset_bottom):
		result.append(bitmap[row][offset_left:-1])
	return result

"""
An array of bytes corresponding to 8-pixel high columns from a simple bitmap (see above).
The columns grabbed begin from the row defined by offset_bottom; the first offset_left columns are skipped.
The trailing zero columns are skipped as well.
"""
def columns_from_simple_bitmap(bitmap, offset_left, offset_bottom):
	
	result = []
	
	base_row = len(bitmap) - 1 - offset_bottom - 7
	
	for current_column in range(offset_left, 16):
		b = 0
		for row in range(0, 8):
			b = b >> 1
			if bitmap[base_row + row][current_column] == '#':
				b |= 0x80
		result.append(b)
	
	while len(result) > 0 and result[-1] == 0:
		result.pop()
	
	return result

vertical_font = {}

code_pattern = re.compile("^[0-9]+$")
for k in font_data.keys():
	if code_pattern.match(k) and min_code <= int(k) and int(k) <= max_code:
		bitmap = font_data[k]
		#if show_bitmaps:
		#	print int(k), bitmap
		sbitmap = simple_bitmap(bitmap)
		if show_bitmaps:
			print '\n'.join(cropped_simple_bitmap(sbitmap, offset_left, offset_bottom))
			print "-" * 50
		columns = columns_from_simple_bitmap(sbitmap, offset_left, offset_bottom)
		if len(columns) > 0:
			vertical_font[int(k)] = columns
		else:
			print(u"Skipping character '%c' because its bitmap is empty" % (int(k),))

max_length = reduce(lambda result, x: max(result, len(x)), vertical_font.values(), 0)
avg_length = int(round(reduce(lambda result, x: result + len(x), vertical_font.values(), 0) / float(len(vertical_font))))

""" 
Appends zeros to the given array, so it has a length specified.
"""
def pad(a, length):
	result = []
	for item in a:
		result.append(item)
	for i in range(len(a), length):
		result.append(0)
	return result

# Let's make sure we have a space character
space = ord(' ')
if min_code <= space and space <= max_code:
	vertical_font[space] = pad([], avg_length)

# Let's remove lowercase letters in case the font should not contain them.
if uppercase_only:
	for ch in range(ord('a'), ord('z') + 1):
		if ch in vertical_font:
			del vertical_font[ch] 

codes = sorted(vertical_font.keys())

ranges = []

range_length = 1
for i in range(1, len(codes)):
	if codes[i] == codes[i - 1] + 1 and i < len(codes):
		range_length += 1
	else:
		ranges.append({ 'first' : codes[i - range_length], 'last' : codes[i - 1] })
		range_length = 1
		
ranges.append({ 'first' : codes[len(codes) - range_length], 'last' : codes[-1] })

"""
Dumps everything in the simplest format.
"""
def print_format1():

	def line_for_code(code, data, max_length):
		s = u"/* '%c' */ %i, " % (ch, len(vertical_font[ch]))
		s += ", ".join(map(str, pad(vertical_font[ch], max_length)))
		s += ","
		return s

	print "/**"
	print " * 8-bit font data generated from '%s'. */" % (font_name,)
	print " */"
	print "class Font8%s {" % (font_name,)
	print "public:"
	print "\tstatic Font8::Data data() {"
	print "\t\tstatic const uint8_t PROGMEM _data[] = {"
	print "\t\t\t// Flags: bit 0 - uppercase only"
	print "\t\t\t%d," % (1 if uppercase_only else 0,)
	first = True
	for r in ranges:
		
		max_length = 0
		for ch in xrange(r['first'], r['last'] + 1):
			max_length = max(max_length, len(vertical_font[ch]))
		
		print u"\t\t\t"
		print u"\t\t\t// Range '%c' to '%c'." % (chr(r['first']), chr(r['last']))
		if first:
			print u"\t\t\t// From/to/bytes per character."
		print u"\t\t\t%d, %d, %d," % (r['first'], r['last'], (1 + max_length),)
		if first:
			print u"\t\t\t"
			print u"\t\t\t// For each character in the range:"
			print u"\t\t\t// Actual width of the character, M;"
			print u"\t\t\t// M bytes with the pixel data of the character, one byte per column of pixels;"
			print u"\t\t\t// K zeros so M + K + 1 = bytes per characters for the range."
		
		for ch in xrange(r['first'], r['last'] + 1):
			print "\t\t\t" + line_for_code(ch, vertical_font[ch], max_length)
			
		first = False

	print ""
	print "\t\t\t// End of all the ranges."
	print "\t\t\t0"
	print "\t\t};"
	print "\t\treturn _data;"
	print "\t}"
	print "};"

print_format1()
