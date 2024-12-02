from metaflow import FlowSpec, step, memray, pypi


class MemrayTorchFlow(FlowSpec):

    @step
    def start(self):
        self.next(self.leaky_torch_routine, self.torch_routine)

    @pypi(python='3.12.0', packages={"torch": "2.4.1", "memray": "1.14.0"})
    @memray()
    @step
    def leaky_torch_routine(self):
        from torch_script import main
        main()
        self.next(self.join)

    @pypi(python='3.12.0', packages={"torch": "2.4.1", "memray": "1.14.0"})
    @memray()
    @step
    def torch_routine(self):
        from torch_script import main
        main(detach=True)
        self.next(self.join)

    @step
    def join(self, inputs):
        self.next(self.end)

    @step
    def end(self):
        pass

if __name__ == '__main__':
    MemrayTorchFlow()