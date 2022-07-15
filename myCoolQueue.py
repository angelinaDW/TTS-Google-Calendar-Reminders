from collections import deque
class myCoolQueue:
    
    def __init__(self):
        self.queue = []
        self._iterationIndex = -1

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
        self._iterationIndex = 0
        return self # this is its own iterable
    

    def __next__(self):
        if self._iterationIndex >= len(self.queue):
            raise StopIteration()
        else:
            tmp = self._iterationIndex
            self._iterationIndex += 1
            return self.queue[tmp]
