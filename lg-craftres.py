import struct
import sys
import threading

images = []
image_info = {}
image_data = {}
image_data_rle = {}

# Helpers
def image_rle_decode(image_rle):
    image_array = []
    for j in range(0, len(image_rle)>>2):
        num, b, g, r = image_rle[j*4:(j+1)*4]
        image_array += [b, g, r] * num
    return image_array

def image_rle_encode(image_raw, width):
    image_rle = bytes([])
    lb = image_raw[0]
    lg = image_raw[1]
    lr = image_raw[2]
    j = 1
    n = 1
    x = 0
    y = 0
    while (True):
        if (j >= len(image_raw)//3):
            image_rle += struct.pack("<BBBB", n, lb, lg, lr)
            break

        b, g, r = image_raw[j*3:(j+1)*3]
        
        if ((b,g,r) != (lb, lg, lr) or n >= 255 or x >= width-1):
            image_rle += struct.pack("<BBBB", n, lb, lg, lr)
            n = 1
        elif ((b,g,r) == (lb, lg, lr)):
            n += 1

        lb = b
        lg = g
        lr = r
        j += 1
        x += 1
        if (x >= width-1):
            x = 0
            y += 1
    return bytes(image_rle)

def image_write(offs, info):
    name, offset, size, width, height, offs_x, offs_y = info
    
    print ("Writing", name, width, height, offs_x, offs_y)
    rle_data = image_data_rle[name]
    offs_new = offset_iter
    size_new = len(rle_data)
    #if (offs_new != offset):
    #    print("Offset mismatch", hex(offs_new), hex(offset))
    #    return size_new
    
    f_out.seek(offs)
    f_out.write(struct.pack("<40sLLLLLL", name.encode('utf-8'), offs_new, size_new, width, height, offs_x, offs_y))
    f_out.seek(offset_iter)
    f_out.write(rle_data)
    
    return size#size_new

def rle_encode_thread(name):
    global image_data
    global image_data_rle
    
    if (name in image_data_rle.keys()):
        return
    
    print ("Encoding", name)
    rle_data = image_rle_encode(image_data[name], width)
    image_data_rle[name] = rle_data
    
    print ("Completed encoding for", name)



#
# MAIN START
#

if len(sys.argv) < 3:
    print ("Usage: lg-craftres.py [raw_resources_a.img] [raw_resources_a_out.img]")
    exit(0)

f = open(sys.argv[1], "rb")
f_out = open(sys.argv[2], "wb")
header = f.read(0x800)

# Header reading
magic, res_table_cnt, version, dev_str, sig_offset = struct.unpack("<16sLL16sQ", header[:0x30])
magic = magic.rstrip(bytes([0x00])).decode('utf-8')
dev_str = dev_str.rstrip(bytes([0x00])).decode('utf-8')
print(magic, hex(res_table_cnt), hex(version), dev_str, sig_offset)

# Copy the original signature (will be invalid by the end but it keeps diffs low)
f.seek(sig_offset)
sig_orig = f.read(0x200)

res_table_offs = 0x800
f.seek(res_table_offs)

# Read all image data
for i in range(0, res_table_cnt):
    f.seek(res_table_offs + i * 0x40)
    res_ent = f.read(0x40)
    name, offset, size, width, height, offs_x, offs_y = struct.unpack("<40sLLLLLL", res_ent)
    name = name.rstrip(bytes([0x00])).decode('utf-8')
    print(name, offset, size, width, height, offs_x, offs_y)
    
    images += [name]
    image_info[name] = (name, offset, size, width, height, offs_x, offs_y)

    f.seek(offset)    
    image_rle = f.read(size)
    image_data_rle[name] = image_rle
    image_array = image_rle_decode(image_rle)
    image_data[name] = image_array

f.close()




#
# Now reconstruct raw_resources_a
#
modify = True
if modify:
    target_name = "LGE_PM_NO_CHARGER"
    target_addr = 0x8056E14;
    target_end_addr = 0x08057000
    shift = (((0x100000000 + target_addr) - 0x90000000) // 3) & 0xFFFFFFFF

    payload_data = open("payload.bin", "rb").read()
    for i in range(target_addr-len(payload_data), ((target_end_addr // 1080) + 1) * 1080):
        payload_data += struct.pack("<L", i & 0xFFFF)

	# Swap in our payload for LGE_PM_NO_CHARGER's data
    del image_data_rle[target_name]
    old_offset = image_info[target_name][1]
    old_size = image_info[target_name][2]
    new_size = len(payload_data)
    image_info[target_name] = (target_name, old_offset, old_size, 1080, len(payload_data)//1080, shift, 0)
    image_data[target_name] = payload_data

# Encode all unencoded data
rle_encode_threads = []
for name in images:
    name, offset, size, width, height, offs_x, offs_y = image_info[name]
    
    t = threading.Thread(target=rle_encode_thread, args=(name,))
    rle_encode_threads += [t]
    
    t.start()

for t in rle_encode_threads:
    t.join()

# Space for header
f_out.seek(0x800)

# Write images
ent_num = 0
offset_iter = 0x1800
offset_unaligned = offset_iter
for name in images:
    size_new = image_write(0x800 + (ent_num * 0x40), image_info[name])
    offset_iter_unaligned = offset_iter + size_new
    offset_iter += (size_new + 0x7FF) & ~0x7FF
    ent_num += 1

# Finalize header
res_table_cnt = ent_num
magic = "BOOT_IMAGE_RLE"
version = 0x1003
dev_str = "cv7a_lao_com"
sig_offset = offset_iter_unaligned

# Write header
f_out.seek(0x0)
f_out.write(struct.pack("<16sLL16sQ", magic.encode('utf-8'), res_table_cnt, version, dev_str.encode('utf-8'), sig_offset))

# We can't sign anything...
f_out.seek(sig_offset)
f_out.write(sig_orig)

# Pad out to the same size as the original partition
f_out.seek(0x3F7E00-1)
f_out.write(bytes([0]))

f_out.close()
