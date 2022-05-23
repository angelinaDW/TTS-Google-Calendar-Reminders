from collections import deque
class myCoolQueue:
    
    def __init_(self):
        '''
        t: The type that things in this queue ought to be
        '''
        self.queue = deque([])

    def take(self) -> object:
        return self.queue.popleft()
    
    def clear(self) -> None:
        self.queue = deque([])
        assert len(self) == 0

    def append(self, e):
        ''' Appends e to the back of the line'''
        self.queue.append(e)

    def length(self) -> int:
        return len(self.queue)

    def __len__(self) -> int:
        return len(self.queue)

