from re import L


count = 0
l = ["["]
for i in range(256):
    l.append("[")
    for j in range(4):
        l.append(str(count))
        if j < 3:
            l.append(",")
        count += 1
    l.append("];")
l.append("]")

print("".join(l))
