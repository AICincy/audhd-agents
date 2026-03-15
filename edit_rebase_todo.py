import os
import sys

def main():
    todo_file = sys.argv[1]
    
    with open(todo_file, "r") as f:
        lines = f.readlines()

    squash_a = ["62c8736", "701eb9a", "402e61c", "2219192"]
    squash_b = ["9ab3a08", "6753b85", "8b676d8", "714a5b9", "50664e7", "7576514", "bc90ed8", "3979259", "e2e44b1", "b032345"]
    squash_c = ["d626ebb", "5eb7c27"] # 5eb7c27 is an internal Initial plan to be squashed

    new_lines = []
    for line in lines:
        if line.startswith("#"):
            new_lines.append(line)
            continue
            
        squash = False
        for c in squash_a + squash_b + squash_c:
            if c in line:
                squash = True
                break
                
        if squash:
            new_lines.append(line.replace("pick ", "squash "))
        else:
            new_lines.append(line)

    with open(todo_file, "w") as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    main()
