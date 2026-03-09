import sys
REGISTER = {
    'zero': "00000",'x0': "00000",
    'ra': "00001",'x1':  "00001",
    'sp': "00010",'x2': "00010",
    'gp': "00011",'x3': "00011",
    'tp': "00100",'x4': "00100",
    't0': "00101",'x5':  "00101",
    't1': "00110",'x6': "00110",
    't2': "00111",'x7': "00111",
    's0': "01000",'fp': "01000",'x8': "01000",
    's1': "01001",'x9': "01001",
    'a0': "01010",'x10': "01010",
    'a1': "01011",'x11': "01011",
    'a2': "01100",'x12': "01100",
    'a3': "01101",'x13': "01101",
    'a4': "01110",'x14': "01110",
    'a5': "01111",'x15': "01111",
    'a6': "10000",'x16': "10000",
    'a7': "10001",'x17': "10001",
    's2': "10010",'x18': "10010",
    's3': "10011",'x19': "10011",
    's4': "10100",'x20': '10100',
    's5': "10101",'x21': "10101",
    's6': "10110",'x22': "10110",
    's7': "10111",'x23': "10111",
    's8': "11000",'x24': '11000',
    's9': "11001",'x25': "11001",
    's10': "11010",'x26': "11010",
    's11': "11011",'x27': "11011",
    't3': "11100",'x28': "11100",
    't4': "11101",'x29': "11101",
    't5': "11110",'x30': "11110",
    't6': "11111",'x31': "11111",
}
def decimal_to_binary(value,bit):
    if value<0:
        value =(1 << bit)+value
    return format(value,f'0{bit}b')
def getting_register(name):
    name =name.strip().lower()
    if name not in REGISTER:
        raise ValueError(f"Invalid register:{name}")
    return REGISTER[name]
# ---------------- INSTRUCTION ENCODERS ---------------- #

def encode_r(f7, rs2, rs1, f3, rd, op):
    return (
        decimal_to_binary(f7,7) +
        rs2 +
        rs1 +
        decimal_to_binary(f3,3) +
        rd +
        decimal_to_binary(op,7)
    )


def encode_i(imm, rs1, f3, rd, op):
    if imm < -2048 or imm > 2047:
        raise ValueError("immediate outside 12-bit range")
    return (
        decimal_to_binary(imm,12) +
        rs1 +
        decimal_to_binary(f3,3) +
        rd +
        decimal_to_binary(op,7)
    )


def encode_s(imm, rs2, rs1, f3, op):
    imm_bin = decimal_to_binary(imm,12)

    return (
        imm_bin[:7] +
        rs2 +
        rs1 +
        decimal_to_binary(f3,3) +
        imm_bin[7:] +
        decimal_to_binary(op,7)
    )

def encode_b(offset, rs2, rs1, f3, op):
    imm = decimal_to_binary(offset,13)
    bit12 = imm[0]
    bit11 = imm[1]
    bit10_5 = imm[2:8]
    bit4_1 = imm[8:12]
    return (
        bit12 +
        bit10_5 +
        rs2 +
        rs1 +
        decimal_to_binary(f3,3) +
        bit4_1 +
        bit11 +
        decimal_to_binary(op,7)
    )


def encode_u(imm, rd, op):
    return decimal_to_binary(imm,20) + rd + decimal_to_binary(op,7)


def encode_j(offset, rd, op):
    imm = decimal_to_binary(offset,21)
    bit20 = imm[0]
    bit10_1 = imm[10:20]
    bit11 = imm[9]
    bit19_12 = imm[1:9]
    return bit20 + bit10_1 + bit11 + bit19_12 + rd + decimal_to_binary(op,7)


def read_imm_register(operand):
    operand =operand.strip()
    if '('not in operand or ')'not in operand:
        raise ValueError(f"Invalid oprands: {operand}")
    parts =operand.split('(')
    if len(parts) != 2:
        raise ValueError(f"not readable: {operand}")
    imm_part =parts[0].strip()
    reg_part = parts[1].rstrip(')').strip()
    if imm_part=="":
        imm= 0
    else:
        try:
            imm = int(imm_part, 0)
        except:
            raise ValueError(f"Invalid imm val: {imm_part}")
    reg =getting_register(reg_part)
    return imm,reg

def assembly(input_file, output_file,readable_file):
    with open(input_file,'r') as f:
        lines = f.readlines()

    labels ={}
    instructions =[]
    pc =0
    errors =[]

    for line in lines:
        line =line.split('#')[0].strip()
        if not line:
            continue

        if':'in line:
            parts =line.split(':', 1)
            label_raw= parts[0]
            label = label_raw.strip()
            if' 'in label_raw.rstrip():
                errors.append(f"invalid ->space before colon : '{label_raw.strip()}'")
            if ' 'in label:
                errors.append(f"Invalid -> contains space: '{label}'")
                continue
            if label in labels:
                errors.append(f"duplicate label: {label}")
            else:
                labels[label] =pc
            line= parts[1].strip()
            if not line:
                continue

        parts= line.replace(',',' ').split()
        if ',,' in line:
            errors.append("oprands are empty")
        if not parts:
            continue
        mnemonic= parts[0].upper()
        instructions.append((pc, mnemonic, parts[1:],line))
        pc +=4
    if not instructions:
        errors.append("missing halt instruction")
    else:
        last_pc,last_m, last_ops,last_raw =instructions[-1]
        is_halt =(
            last_m =='BEQ'and
            len(last_ops)>= 3 and
            last_ops[0].strip() in ('zero','x0') and
            last_ops[1].strip() in ('zero', 'x0')
        )
        if not is_halt:
            errors.append("missing halt or not in last")
    if errors:
        for e in errors:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    binary_lines = []
    readable_lines =[]
    for (pc, mnemonic,operands,raw) in instructions:
        try:
            binary = instruction_encoding(mnemonic,operands,labels, pc)
            binary_lines.append(binary)
            readable_lines.append(f"PC={pc:08x}: {raw} -> {binary}")
        except Exception as e:
            print(f"Error at PC {pc}: {raw}\n  {e}",file=sys.stderr)
            sys.exit(1)

    with open(output_file,'w') as f:
        f.write('\n'.join(binary_lines) +'\n')

    if readable_file:
        with open(readable_file, 'w')as f:
            f.write('\n'.join(readable_lines) + '\n')

def instruction_encoding(mnemonic,operands,labels, pc):
    m = mnemonic.lower()
    def check_ops(n):
        if len(operands)!= n:
            raise ValueError(f"{m} req {n} operands and got {len(operands)}")
    def reg(i):
        return get_register(operands[i])
    def label_offset(i):
        s = operands[i].strip()
        if s in labels:
            offset = labels[s] -pc
            if offset % 4 != 0:
                raise ValueError("offset is not in correct position")
            return offset
        try:
            return int(s, 0)
        except:
            raise ValueError(f"unknown label or immediate: {s}")
    if m =='add':
        check_ops(3)
        rd, rs1, rs2 = reg(0),reg(1),reg(2)
        return encode_r(0b0000000,rs2,rs1,0b000, rd,0b0110011)
    elif m =='sub':
        check_ops(3)
        rd,rs1,rs2 =reg(0),reg(1),reg(2)
        return encode_r(0b0100000,rs2, rs1,0b000, rd,0b0110011)
    elif m =='slt':
        check_ops(3)
        rd,rs1,rs2 = reg(0),reg(1),reg(2)
        return encode_r(0b0000000, rs2, rs1, 0b010, rd, 0b0110011)
    elif m =='sltu':
        check_ops(3)
        rd, rs1,rs2 = reg(0),reg(1),reg(2)
        return encode_r(0b0000000,rs2,rs1,0b011,rd, 0b0110011)
    elif m =='and':
        check_ops(3)
        rd,rs1,rs2 =reg(0), reg(1),reg(2)
        return encode_r(0b0000000, rs2, rs1, 0b111, rd, 0b0110011)
    elif m =='or':
        check_ops(3)
        rd, rs1,rs2 = reg(0),reg(1),reg(2)
        return encode_r(0b0000000,rs2, rs1,0b110, rd,0b0110011)
    elif m =='xor':
        check_ops(3)
        rd,rs1,rs2 = reg(0),reg(1),reg(2)
        return encode_r(0b0000000, rs2,rs1, 0b100,rd,0b0110011)
    elif m =='sll':
        check_ops(3)
        rd,rs1,rs2 = reg(0),reg(1),reg(2)
        return encode_r(0b0000000, rs2,rs1, 0b001,rd,0b0110011)
    elif m =='srl':
        check_ops(3)
        rd,rs1, rs2 = reg(0), reg(1), reg(2)
        return encode_r(0b0000000,rs2,rs1, 0b101,rd,0b0110011)
    
    elif m=='addi':
        check_ops(3)
        rd,rs1 =reg(0), reg(1)
        imm= label_offset(2)
        return encode_i(imm,rs1, 0b000,rd, 0b0010011)
    elif m =='sltiu':
        check_ops(3)
        rd,rs1= reg(0),reg(1)
        imm =label_offset(2)
        return encode_i(imm ,rs1, 0b011,rd, 0b0010011)
    elif m =='lw':
        check_ops(2)
        rd =reg(0)
        imm,rs1= read_imm_register(operands[1])
        return encode_i(imm,rs1,0b010, rd,0b0000011)
    elif m == 'jalr':
        check_ops(3)
        rd, rs1 = reg(0),reg(1)
        imm =int(operands[2].strip(),0)
        return encode_i(imm, rs1,0b000, rd,0b1100111)
    elif m =='sw':
        check_ops(2)
        rs2 =reg(0)
        imm,rs1 =read_imm_register(operands[1])
        return encode_i(imm,rs2, rs1,0b010,0b0100011)
    elif m =='beq':
        check_ops(3)
        rs1,rs2 =reg(0),reg(1)
        offset =label_offset(2)
        return encode_b(offset,rs2,rs1,0b000,0b1100011)
    elif m =='bne':
        check_ops(3)
        rs1,rs2 =reg(0),reg(1)
        offset= label_offset(2)
        return encode_b(offset, rs2,rs1,0b001, 0b1100011)
    elif m =='blt':
        check_ops(3)
        rs1, rs2 =reg(0), reg(1)
        offset= label_offset(2)
        return encode_b(offset,rs2, rs1,0b100, 0b1100011)
    elif m =='bge':
        check_ops(3)
        rs1, rs2= reg(0), reg(1)
        offset =label_offset(2)
        return encode_b(offset,rs2, rs1,0b101, 0b1100011)
    elif m =='bltu':
        check_ops(3)
        rs1,rs2= reg(0),reg(1)
        offset =label_offset(2)
        return encode_b(offset, rs2,rs1,0b110,0b1100011)
    elif m =='bgeu':
        check_ops(3)
        rs1, rs2 = reg(0),reg(1)
        offset =label_offset(2)
        return encode_b(offset,rs2, rs1,0b111,0b1100011)
    elif m == 'jal':
        check_ops(2)
        rd =reg(0)
        offset= label_offset(1)
        return encode_j(offset, rd,0b1101111)
    elif m =="lui":
        check_ops(2)
        rd =reg(0)
        imm =int(operands[1].strip(),0)
        return encode_u(imm,rd,0b0110111)
    elif m =='auipc':
        check_ops(2)
        rd= reg(0)
        imm =int(operands[1].strip(), 0)
        return encode_u(imm,rd,0b0010111)
    else:
        raise ValueError(f"Unknown instruction: {m}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 Assembler.py <input.asm><output.bin> [readable.txt]")
        sys.exit(1)
    input_file =sys.argv[1]
    output_file= sys.argv[2]
    if len(sys.argv) >3:
        readable_file = sys.argv[3]
    else:
        readable_file= None
    assembly(input_file,output_file,readable_file)