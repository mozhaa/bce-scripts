import sys
import os

'''
Usage: python remove_trash.py <input> <output>

Удаляет дубликаты и вложенные пары клонов из файла input, 
и выводит результат в output
'''

class progressbar:
    width = 20
    
    def __init__(self, maxval: int, startval: int):
        self.maxval = maxval
        self.val = startval
    
    def perc(self, val=None):
        if val is None:
            val = self.val
        return val / self.maxval
    
    def perc_number(self, val=None):
        return int(self.perc(val) * 100)
    
    def show(self):
        blocks = int(self.perc() * progressbar.width) 
        print(f'\r[{"#" * blocks}{"." * (progressbar.width - blocks)}]\t{self.perc_number()}%', end="")
        sys.stdout.flush()
            
    def update(self, val):
        if self.perc_number(val) > self.perc_number():
            self.val = val
            self.show()
    
    def end(self):
        print()

class codeblock:
    def __init__(self, fn: str, begin: int, end: int):
        self.fn = fn
        self.begin = begin
        self.end = end
    
    def __repr__(self):
        return f'{self.fn},{self.begin},{self.end}'
    
    def is_inside(self, b: "codeblock"):
        if self.fn != b.fn:
            return False
        return self.begin >= b.begin and self.end <= b.end    
    
    def is_equal(self, b: "codeblock"):
        if self.fn != b.fn:
            return False
        return self.begin == b.begin and self.end == b.end

class clonepair:
    def __init__(self, s: str):
        dir1, fn1, begin1, end1, dir2, fn2, begin2, end2 = s.split(',')
        self.b1 = codeblock(f'{dir1},{fn1}', int(begin1), int(end1))
        self.b2 = codeblock(f'{dir2},{fn2}', int(begin2), int(end2))
        if self.b1.fn < self.b2.fn:
            self.b1, self.b2 = self.b2, self.b1
    
    def __repr__(self):
        return f'{self.b1.__repr__()},{self.b2.__repr__()}'
    
    @classmethod
    def duplicate(cls, p1: "clonepair", p2: "clonepair"):
        if p1.b1.is_equal(p2.b1) and p1.b2.is_equal(p2.b2):
            return True
        return False
    
    @classmethod
    def nested(cls, p1: "clonepair", p2: "clonepair"):
        if p1.b1.is_inside(p2.b1) and p1.b2.is_inside(p2.b2):
            return True
        if p2.b1.is_inside(p1.b1) and p2.b2.is_inside(p1.b2):
            return True
        return False

def sort(ifn: str, ofn: str):
    with open(ifn, "r") as f:
        lines = f.readlines()
    lines = list(map(lambda line: clonepair(line.rstrip()).__repr__() + '\n', lines))
    with open(ofn, "w") as f:
        f.writelines(lines)

def shrink_block(block: list[clonepair]):
    result = []
    duplicates = 0
    nested = 0
    total = 0
    for cp1 in block:
        approved = True
        total += 1
        for cp2 in result:
            if clonepair.duplicate(cp1, cp2):
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

def shrink(ifn: str, ofn: str):
    print("Sorting... ", end="")
    sys.stdout.flush()
    tmpfn = f'{ifn}_tmp'
    sort(ifn, tmpfn)
    os.system(f'sort -t \',\' -k1,2 -k5,6 "{tmpfn}" >"{tmpfn}_tmp"')
    os.system(f'rm -f {tmpfn}')
    print("done.")
    sys.stdout.flush()
    tmpfn = tmpfn + "_tmp"
    total_lines = lines_in_file(tmpfn)
    current_line = 0
    progress = progressbar(total_lines, current_line)
    with open(tmpfn, "r") as f, open(ofn, "w") as of:
        block = []
        prev_block_fn = ''
        duplicates = 0
        nested = 0
        total = 0
        for line in f:
            current_line += 1
            progress.update(current_line)
            
            cp = clonepair(line)
            block_fn = f'{cp.b1.fn};{cp.b2.fn}'
            if block_fn != prev_block_fn:
                sblock, bduplicates, bnested, btotal = shrink_block(block)
                write_block(sblock, of)
                duplicates += bduplicates
                nested += bnested
                total += btotal
                prev_block_fn = block_fn
                block = []
            block.append(cp)
        sblock, bduplicates, bnested, btotal = shrink_block(block)
        write_block(sblock, of)
        duplicates += bduplicates
        nested += bnested
        total += btotal
    progress.end()
    print(f'total input:\t{total} pairs\n')
    print(f'approved:\t{total - duplicates - nested} pairs ({round((total - duplicates - nested) / total * 100, 5)}%)')
    print(f'duplicates:\t{duplicates} pairs ({round(duplicates / total * 100, 5)}%)')
    print(f'nested:\t\t{nested} pairs ({round(nested / total * 100, 5)}%)')
    os.system(f'rm -f {tmpfn}')
                

def main():
    ifn = sys.argv[1]
    ofn = sys.argv[2]
    shrink(ifn, ofn)

if __name__ == "__main__":
    main()