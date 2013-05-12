
all: marux.rdump.2.bin marux.r.2.bin

marux.rdump.2.bin: marux.r.2.bin 
	cat $< | xxd -u > $@

marux.r.2.bin: output/font/marux.bin
	cat $< | python -c 'import sys; sys.stdout.write(sys.stdin.read()[::-1])' > $@

marux.r.bin: marux.bin
	cat $< | python -c 'import sys; sys.stdout.write(sys.stdin.read()[::-1])' > $@

marux.rdump.bin: marux.r.bin
	cat $< | xxd -u > $@
