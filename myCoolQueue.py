from collections import deque
class myCoolQueue:
    
    def __init__(self):
        self.queue = []

    def take(self) -> object:
        return self.queue.pop(0)
    
    def clear(self) -> None:
        self.queue = []
        assert len(self) == 0

    def append(self, e):
        ''' Appends e to the back of the line'''
        self.queue.append(e)

    def length(self) -> int:
        return len(self.queue)

    def __len__(self) -> int:
        return len(self.queue)

    def sort(self):
        # assumes this queue contains events that should be sorted by starting event
        self.queue.sort()
        # todo: test this method

    def __iter__(self):
        self.queue.__iter__()
