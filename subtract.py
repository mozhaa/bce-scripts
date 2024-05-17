import sys
import os
import time
import tempfile

helpmsg = \
'''
Usage: python subtract.py [-t threshold (default: 1.0)] <input1> <input2> <output>

Вычитает один набор пар клонов из другого (из input1 вычитает input2).
Пара клонов убирается из input1, если её дубликат есть в input2.
Результат выводится в output.

Дубликаты определяются с точностью до threshold, так же как и в
BigCloneEval: 
- если общая часть двух блоков кода содержится в каждом из этих
  двух блоков хотя бы на threshold * 100%, то эти блоки кода 
  считаются совпадающими
- если у двух пар клонов оба соответствующих блока совпадают по
  определению выше, то эти пары клонов считают дубликатами, и одна
  из них удаляется.
'''

class progressbar:
    width = 20
    
    def __init__(self, maxval: int, startval: int, precision: int = 0):
        self.maxval = maxval
        self.val = startval
        self.realval = startval
        self.precision = precision
        
        self.startval = startval
        self.starttime = time.time()
        self.prevtime = self.starttime
    
    def perc(self, val=None):
        if val is None:
            val = self.val
        return val / self.maxval
    
    def perc_number(self, val=None):
        return round(self.perc(val) * 100, self.precision)
    
    def eta(self):
        return round((time.time() - self.starttime) * (self.maxval - self.realval) / (self.realval - self.startval), 2)
    
    def elapsed(self):
        return self.prevtime - self.starttime
    
    def get_output(self):
        blocks = int(self.perc() * progressbar.width) 
        fmt = f'\r\33[2K[{{}}{{}}]\t{{: 3.{self.precision}f}}%\tETA: {{:.2f}} s\tELAPSED: {{:.2f}} s'
        return fmt.format("#" * blocks, "." * (progressbar.width - blocks), self.perc_number(), self.eta(), self.elapsed())
    
    def show(self):
        print(self.get_output(), end="")
        sys.stdout.flush()
    
    def update(self, val):
        if round(self.perc_number(val), self.precision) > round(self.perc_number(), self.precision):
            curr_time = time.time()
            if time.time() - self.prevtime > 0.5:
                self.val = val
                self.prevtime = curr_time
                self.show()
    
    def increment(self):
        self.realval += 1
        self.update(self.realval)
    
    def end(self):
        self.val = self.maxval
        self.prevtime = time.time()
        self.show()
        print()

class codeblock:
    def __init__(self, fn: str, begin: int, end: int):
        self.fn = fn
        self.begin = begin
        self.end = end
    
    def __repr__(self):
        return f'{self.fn},{self.begin},{self.end}'
    
    def length(self):
        return self.end - self.begin
    
    def is_inside(self, b: "codeblock"):
        if self.fn != b.fn:
            return False
        return self.begin >= b.begin and self.end <= b.end    
    
    def is_equal(self, b: "codeblock", threshold: float = 1.0):
        if self.fn != b.fn:
            return False
        common_length = min(self.end, b.end) - max(self.begin, b.begin)
        return (common_length / self.length() >= threshold) and (common_length / b.length() >= threshold)

class clonepair:
    def __init__(self, s: str, filenum: int):
        self.filenum = filenum
        dir1, fn1, begin1, end1, dir2, fn2, begin2, end2 = s.split(',')
        self.b1 = codeblock(f'{dir1},{fn1}', int(begin1), int(end1))
        self.b2 = codeblock(f'{dir2},{fn2}', int(begin2), int(end2))
        if self.b1.fn < self.b2.fn:
            self.b1, self.b2 = self.b2, self.b1
    
    def __repr__(self):
        return f'{self.b1.__repr__()},{self.b2.__repr__()}'
    
    @classmethod
    def from_debug(cls, s: str):
        filenum = s.split(',')[-1]
        repr = ','.join(s.split(',')[:-1])
        return cls(repr, int(filenum))
    
    def debug_print(self):
        return f'{self.b1.__repr__()},{self.b2.__repr__()},{self.filenum}'
    
    def get_filepair(self):
        return f'{self.b1.fn};{self.b2.fn}'
    
    @classmethod
    def duplicate(cls, p1: "clonepair", p2: "clonepair", threshold: float = 1.0):
        if p1.b1.is_equal(p2.b1, threshold=threshold) and p1.b2.is_equal(p2.b2, threshold=threshold):
            return True
        return False
    

def sort_lines(ifn: str, total_lines: int):
    td = tempfile.mkdtemp()
    batch_size = 500000
    total_files = (total_lines + batch_size - 1) // batch_size
    
    cmd = f'''
split -l {batch_size} "{ifn}" {td}/
i=0
for f in {td}/*
do
    i=$((i+1))
    echo -n "\\r$((100*i/{total_files}))%"
    sort -t ',' -k1,2 -k5,6 "$f" -o "$f"
done
echo -n "\\ndone.\\nMerging... "
sort -t ',' -k1,2 -k5,6 -m {td}/* -o "{ifn}"
rm -rf {td}/
    '''
    os.system(cmd)

def shrink_block(block: list[clonepair], threshold: float):
    result = []
    for cp1 in block:
        approved = True
        for cp2 in result:
            if clonepair.duplicate(cp1, cp2, threshold=threshold):
                approved = False
                break
        if approved:
            result.append(cp1)
    return result

def subtract_blocks(block1: list[clonepair], block2: list[clonepair], threshold: float, progress: progressbar):
    result = []
    block2 = shrink_block(block2, threshold)
    for cp in block1:
        progress.increment()
        add = True
        for xcp in result:
            if clonepair.duplicate(cp, xcp, threshold):
                add = False
                break
        for xcp in block2:
            if clonepair.duplicate(cp, xcp, threshold):
                add = False
                break
        if add:
            result.append(cp)
    return result

def write_block(block: list[clonepair], of):
    of.writelines([cp.__repr__() + "\n" for cp in block])

def lines_in_file(fn: str):
    with open(fn, "rb") as f:
        num_lines = sum(1 for _ in f)
    return num_lines

def concat_files(ifn1: str, ifn2: str, total_lines: int):
    tf = tempfile.NamedTemporaryFile(mode="w", delete=False)
    progress = progressbar(total_lines, 0, 0)
    with open(ifn1, "r") as f:
        for line in f:
            cp = clonepair(line, 1)
            tf.write(cp.debug_print() + '\n')
            progress.increment()
    with open(ifn2, "r") as f:
        for line in f:
            cp = clonepair(line, 2)
            tf.write(cp.debug_print() + '\n')
            progress.increment()
    progress.end()
    tf.close()
    return tf.name

def subtract(ifn1: str, ifn2: str, ofn: str, threshold: float):
    start = time.time()
    
    print("Counting lines... ", end="")
    sys.stdout.flush()
    total_lines1 = lines_in_file(ifn1)
    total_lines2 = lines_in_file(ifn2)
    total_lines = total_lines1 + total_lines2
    print("done.")
    sys.stdout.flush()
    
    print("Concatenating files... ")
    sys.stdout.flush()
    tfn = concat_files(ifn1, ifn2, total_lines)
    print("done.")
    sys.stdout.flush()
    
    print(f'Temporary file: "{tfn}"')
    
    print("Sorting all lines... ")
    sys.stdout.flush()
    sort_lines(tfn, total_lines)
    print("\ndone.")
    sys.stdout.flush()
    
    
    progress = progressbar(total_lines1, 0, 4)
    
    with open(tfn, "r") as f, open(ofn, "w") as of:
        keeped = 0
        total = 0
        
        block1 = []
        block2 = []
        prev_filepair = ''
        for line in f:
            cp = clonepair.from_debug(line)
            curr_filepair = cp.get_filepair()
            if curr_filepair != prev_filepair:
                # End of block with same filepair
                sblock = subtract_blocks(block1, block2, threshold, progress)
                write_block(sblock, of)
                keeped += len(sblock)
                
                prev_filepair = curr_filepair
                block1 = []
                block2 = []
            if cp.filenum == 1:
                total += 1
                block1.append(cp)
            else:
                block2.append(cp)
        
        sblock = subtract_blocks(block1, block2, threshold, progress)
        write_block(sblock, of)
        keeped += len(sblock)
        
    progress.end()
    print(f'Total lines, before subtracting:\t{total} pairs\n')
    print(f'Keeped lines:\t\t\t\t{keeped} pairs ({round((keeped) / total * 100, 5)}%)')
    print(f'Removed lines:\t\t\t\t{total - keeped} pairs ({round((total - keeped) / total * 100, 5)}%)')
    print(f'\nElapsed time: {round(time.time() - start, 2)} s')
    os.system(f'rm -f {tfn}')
                
def help():
    print(helpmsg)
    exit(0)

def main():
    threshold = 1.0
    ifn1 = None
    ifn2 = None
    ofn = None
    i = 1
    while (i < len(sys.argv)):
        if sys.argv[i] == '-t':
            i += 1
            threshold = float(sys.argv[i])
        elif ifn1 is None:
            ifn1 = sys.argv[i]
        elif ifn2 is None:
            ifn2 = sys.argv[i]
        elif ofn is None:
            ofn = sys.argv[i]
        else:
            help()
        i += 1
    if threshold <= 0 or threshold > 1:
        print("Threshold must be in [0.0, 1.0] range.")
        exit(0)
    if ifn1 is None or ifn2 is None or ofn is None:
        help()
            
    subtract(ifn1, ifn2, ofn, threshold)

if __name__ == "__main__":
    main()