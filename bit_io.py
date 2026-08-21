class BitWriter:
    def __init__(self):
        self.buffer = bytearray()
        self.current_byte =0
        self.bit_count = 0
    def write_bit(self,bit):
        self.current_byte = (self.current_byte<<1) | bit
        self.bit_count+=1
        if self.bit_count == 8:
            self.buffer.append(self.current_byte)
            self.current_byte = 0
            self.bit_count = 0

    def write_bits(self,value,width):
        for i in range(width):
            self.write_bit((value>>(width-1-i))&1)


    def pad_trailer(self):
        if self.bit_count<=5:
            self.current_byte = self.current_byte<<(5-self.bit_count)
            self.current_byte = (self.current_byte<<1) | (self.bit_count>>2)
            self.current_byte = (self.current_byte<<1) | ((self.bit_count>>1)&1)
            self.current_byte = (self.current_byte<<1) | (self.bit_count&1)
            self.buffer.append(self.current_byte)
        else:
            self.current_byte = self.current_byte<<(8-self.bit_count)
            self.buffer.append(self.current_byte)
            self.current_byte = self.bit_count
            self.buffer.append(self.current_byte)

    def __len__(self):
        return len(self.buffer)*8

    def data(self):
        return self.buffer




class BitReader:
    def __init__(self,data):
        self.data = data
        self.byte_pos=0
        self.bit_pos=0
        self.last_valid_bit_pos = ((self.data[-1])&(0b111))
        if self.last_valid_bit_pos<=5:
            self.last_byte = len(self.data)-1
        else:
            self.last_byte = len(self.data)-2
    def read_bit(self):
        if self.byte_pos>=len(self.data):
            raise EOFError("Run out of bits to read")
        byte = self.data[self.byte_pos]
        bit = (byte>>(7-self.bit_pos))&1
        self.bit_pos+=1

        if self.bit_pos==8:
            self.bit_pos = 0
            self.byte_pos+=1

        return bit

    def read_bits(self,n):
        if self.byte_pos==self.last_byte:
            if self.bit_pos == self.last_valid_bit_pos:
                return -1 ##End of data aka game is over here
        value = 0
        for _ in range(n):
            value = (value<<1)|self.read_bit()
        return value

    def bits_remaining(self):
        return (len(self.data)- self.byte_pos)*8-self.bit_pos




 
def main():
    w = BitWriter()

    w.write_bits(0b101101,7)
    w.write_bits(0b10,2)
    w.pad_trailer()
    data = w.data()
    r = BitReader(data)
    print(r.read_bits(7))
    print(r.read_bits(2))
    print(r.read_bits(1))

if __name__ =="__main__":
    main()