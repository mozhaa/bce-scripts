import sys
import os
import time
import tempfile

helpmsg = \
'''
Usage: python remove_trash.py [-t threshold (default: 1.0)] <input> <output>

Удаляет дубликаты и вложенные пары клонов из файла input, 
и выводит результат в output.

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
    
    def __init__(self, maxval: int, startval: int):
        self.maxval = maxval
        self.val = startval
        self.realval = startval
        
        self.startval = startval
        self.starttime = time.time()
    
    def perc(self, val=None):
        if val is None:
            val = self.val
        return val / self.maxval
    
    def perc_number(self, val=None):
        return int(self.perc(val) * 100)
    
    def eta(self):
        return round((time.time() - self.starttime) * (self.maxval - self.realval) / (self.realval - self.startval), 2)
    
    def get_output(self):
        blocks = int(self.perc() * progressbar.width) 
        return f'\r\33[2K[{"#" * blocks}{"." * (progressbar.width - blocks)}]\t{self.perc_number()}%\tETA: {self.eta()} s'
    
    def show(self):
        print(self.get_output(), end="")
        sys.stdout.flush()
    
    def update(self, val):
        if self.perc_number(val) > self.perc_number():
            self.val = val
            self.show()
    
    def increment(self):
        self.realval += 1
        self.update(self.realval)
    
    def end(self):
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
    def __init__(self, s: str):
        dir1, fn1, begin1, end1, dir2, fn2, begin2, end2 = s.split(',')
        self.b1 = codeblock(f'{dir1},{fn1}', int(begin1), int(end1))
        self.b2 = codeblock(f'{dir2},{fn2}', int(begin2), int(end2))
        if self.b1.fn < self.b2.fn:
            self.b1, self.b2 = self.b2, self.b1
    
    def __repr__(self):
        return f'{self.b1.__repr__()},{self.b2.__repr__()}'
    
    def get_filepair(self):
        return f'{self.b1.fn};{self.b2.fn}'
    
    @classmethod
    def duplicate(cls, p1: "clonepair", p2: "clonepair", threshold: float = 1.0):
        if p1.b1.is_equal(p2.b1, threshold=threshold) and p1.b2.is_equal(p2.b2, threshold=threshold):
            return True
        return False
    
    @classmethod
    def nested(cls, p1: "clonepair", p2: "clonepair"):
        if p1.b1.is_inside(p2.b1) and p1.b2.is_inside(p2.b2):
            return True
        if p2.b1.is_inside(p1.b1) and p2.b2.is_inside(p1.b2):
            return True
        return False

def sort_file_order(ifn: str, total_lines: int):
    tf = tempfile.NamedTemporaryFile(mode="w", delete=False)
    progress = progressbar(total_lines, 0)
    with open(ifn, "r") as f:
        for line in f:
            tf.write(clonepair(line).__repr__() + '\n')
            progress.increment()
    progress.end()
    tf.close()
    return tf.name

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
    duplicates = 0
    nested = 0
    total = 0
    for cp1 in block:
        approved = True
        total += 1
        for cp2 in result:
            if clonepair.duplicate(cp1, cp2, threshold=threshold):
                duplicates += 1
                approved = False
                break
            if clonepair.nested(cp1, cp2):
                nested += 1
                approved = False
                break
        if approved:
            result.append(cp1)
    return (result, duplicates, nested, total)

def write_block(block: list[clonepair], of):
    of.writelines([cp.__repr__() + "\n" for cp in block])

def lines_in_file(fn: str):
    with open(fn, "rb") as f:
        num_lines = sum(1 for _ in f)
    return num_lines

def shrink(ifn: str, ofn: str, threshold: float):
    start = time.time()
    
    print("Counting lines... ", end="")
    sys.stdout.flush()
    total_lines = lines_in_file(ifn)
    print("done.")
    sys.stdout.flush()
    
    print("Sorting each line... ")
    sys.stdout.flush()
    tfn = sort_file_order(ifn, total_lines)
    print("done.")
    sys.stdout.flush()
    
    print(f'Temporary file: "{tfn}"')
    
    print("Sorting all lines... ")
    sys.stdout.flush()
    sort_lines(tfn, total_lines)
    print("\ndone.")
    sys.stdout.flush()
    
    
    progress = progressbar(total_lines, 0)
    
    with open(tfn, "r") as f, open(ofn, "w") as of:
        duplicates = 0
        nested = 0
        total = 0
        
        block = []
        prev_filepair = ''
        for line in f:
            progress.increment()
            
            cp = clonepair(line)
            curr_filepair = cp.get_filepair()
            if curr_filepair != prev_filepair:
                # End of block with same filepair
                sblock, bduplicates, bnested, btotal = shrink_block(block, threshold)
                write_block(sblock, of)
                
                duplicates += bduplicates
                nested += bnested
                total += btotal
                
                prev_filepair = curr_filepair
                block = []
            block.append(cp)
        
        sblock, bduplicates, bnested, btotal = shrink_block(block, threshold)
        write_block(sblock, of)
        
        duplicates += bduplicates
        nested += bnested
        total += btotal
    progress.end()
    print(f'Total input:\t{total} pairs\n')
    print(f'Approved:\t{total - duplicates - nested} pairs ({round((total - duplicates - nested) / total * 100, 5)}%)')
    print(f'Duplicates:\t{duplicates} pairs ({round(duplicates / total * 100, 5)}%)')
    print(f'Nested:\t\t{nested} pairs ({round(nested / total * 100, 5)}%)')
    print(f'\nElapsed time: {round(time.time() - start, 2)} s')
    os.system(f'rm -f {tfn}')
                
def help():
    print(helpmsg)
    exit(0)

def main():
    threshold = 1.0
    ifn = None
    ofn = None
    i = 1
    while (i < len(sys.argv)):
        if sys.argv[i] == '-t':
            i += 1
            threshold = float(sys.argv[i])
        elif ifn is None:
            ifn = sys.argv[i]
        elif ofn is None:
            ofn = sys.argv[i]
        else:
            help()
        i += 1
    if threshold <= 0 or threshold > 1:
        print("Threshold must be in [0.0, 1.0] range.")
        exit(0)
            
    shrink(ifn, ofn, threshold)

if __name__ == "__main__":
    main()