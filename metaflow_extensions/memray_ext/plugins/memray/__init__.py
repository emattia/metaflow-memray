class memray_deco:

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, step_func):
        from metaflow import _memray, card

        flame_card = card(type="memray_flamegraph")
        table_card = card(type="memray_table")
        allocator_card = card(type="memray_allocator")
        return flame_card(
            table_card(
                allocator_card(
                    _memray(**self.kwargs)(step_func)
                )
            )
        )