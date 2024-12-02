from metaflow import FlowSpec, step, memray, pypi


class MemrayNumpyFlow(FlowSpec):

    @step
    def start(self):
        self.next(self.do_smth)

    @pypi(python='3.12.0', packages={"numpy": "2.1.1", "memray": "1.14.0"})
    @memray(native_traces=True)
    @step
    def do_smth(self):
        import numpy as np
        a = np.random.rand(1000, 1000)
        b = np.random.rand(1000, 1000)
        c = a @ b
        d = np.random.rand(2000, 1000)
        e = d @ b
        f = np.random.rand(3000, 2000)
        g = f @ e
        self.next(self.end)

    @step
    def end(self):
        pass

if __name__ == '__main__':
    MemrayNumpyFlow()