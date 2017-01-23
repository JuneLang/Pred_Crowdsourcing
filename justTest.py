class AAA():
    def __init__(self):
        return

a = AAA()
a.t = 1

b = AAA()
b.t = 2

c = AAA()
c.t = 3

list = [c,b,a]

list.sort(key=lambda x: x.t)

print(list)