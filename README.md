# CVE-2020-12753-PoC
This repo contains a proof-of-concept for 🔋📱❄️🥾🔓, an SBL1/aboot vuln for Secure EL3 arbitrary code execution on the LG Stylo 4 (AMZ/Q710ULM). This is only tested on updates 20a and 20c and with the SBL1 variant of the vulnerability.

```
 - Makefile                 : Builds raw_resources_a_mod.img given sbl_rop.s and raw_resources.img_884736
 - raw_resources.img_884736 : Original raw_resources partition; sha256 510def86aa7608ac02f243d3c161bf973ac4add066be763c8abcb2fee90a454c
 - raw_resources_a_mod.img  : pre-compiled raw_resources partition to be flashed; sha256 26ee5f4589009bc20269bdb813a78d729b9daba44f7826560f6b7201f5396e73
 - payload.bin              : pre-compiled output of sbl_rop.s (no RLE compression)
 - lg-craftres.py           : Python3 script which takes in raw_resources.img_884736 and payload.bin and outputs raw_resources_a_mod.img
 - sbl_rop.s                : ROP payload to be written to the stack by load_res_888rle_image
 - sbl_gadgets.s            : ROP gadget defines for SBL1, included by sbl_rop.s
```

To build from source, armips (https://github.com/Kingcom/armips) and Python 3 are required.
