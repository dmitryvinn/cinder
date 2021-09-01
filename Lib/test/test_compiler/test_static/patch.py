import asyncio
import re
from unittest.mock import Mock, patch

from .common import StaticTestBase


class StaticPatchTests(StaticTestBase):
    def test_patch_function(self):
        codestr = """
            def f():
                return 42

            def g():
                return f()
        """
        with self.in_module(codestr) as mod:
            g = mod["g"]
            for i in range(100):
                g()
            with patch(f"{mod['__name__']}.f", autospec=True, return_value=100) as p:
                self.assertEqual(g(), 100)

    def test_patch_async_function(self):
        codestr = """
            class C:
                async def f(self) -> int:
                    return 42

                def g(self):
                    return self.f()
        """
        with self.in_module(codestr) as mod:
            C = mod["C"]
            c = C()
            for i in range(100):
                try:
                    c.g().send(None)
                except StopIteration as e:
                    self.assertEqual(e.args[0], 42)

            with patch(f"{mod['__name__']}.C.f", autospec=True, return_value=100) as p:
                try:
                    c.g().send(None)
                except StopIteration as e:
                    self.assertEqual(e.args[0], 100)

    def test_patch_async_method_incorrect_type(self):
        codestr = """
            class C:
                async def f(self) -> int:
                    return 42

                def g(self):
                    return self.f()
        """
        with self.in_module(codestr) as mod:
            C = mod["C"]
            c = C()
            for i in range(100):
                try:
                    c.g().send(None)
                except StopIteration as e:
                    self.assertEqual(e.args[0], 42)

            with patch(
                f"{mod['__name__']}.C.f", autospec=True, return_value="not an int"
            ):
                with self.assertRaises(TypeError):
                    c.g().send(None)

    def test_patch_async_method_raising(self):
        codestr = """
            class C:
                async def f(self) -> int:
                    return 42

                def g(self):
                    return self.f()
        """

        def raise_error(self):
            raise IndexError("failure!")

        with self.in_module(codestr) as mod:
            C = mod["C"]
            c = C()
            for i in range(100):
                try:
                    c.g().send(None)
                except StopIteration as e:
                    self.assertEqual(e.args[0], 42)

            with patch(f"{mod['__name__']}.C.f", raise_error):
                with self.assertRaises(IndexError):
                    c.g().send(None)

    def test_patch_async_method_non_coroutine(self):
        codestr = """
            class C:
                async def f(self) -> int:
                    return 42

                def g(self):
                    return self.f()
        """

        loop = asyncio.new_event_loop()

        def future_return(self):
            fut = loop.create_future()
            fut.set_result(100)
            return fut

        with self.in_module(codestr) as mod:
            C = mod["C"]
            c = C()
            for i in range(100):
                try:
                    c.g().send(None)
                except StopIteration as e:
                    self.assertEqual(e.args[0], 42)

            with patch(f"{mod['__name__']}.C.f", future_return):
                asyncio.run(c.g())

        loop.close()

    def test_patch_parentclass_slot(self):
        codestr = """
        class A:
            def f(self) -> int:
                return 3

        class B(A):
            pass

        def a_f_invoker() -> int:
            return A().f()

        def b_f_invoker() -> int:
            return B().f()
        """
        with self.in_module(codestr) as mod:
            A = mod["A"]
            a_f_invoker = mod["a_f_invoker"]
            b_f_invoker = mod["b_f_invoker"]
            setattr(A, "f", lambda _: 7)

            self.assertEqual(a_f_invoker(), 7)
            self.assertEqual(b_f_invoker(), 7)

    def test_self_patching_function(self):
        codestr = """
            def x(d, d2=1): pass
            def removeit(d):
                global f
                f = x

            def f(d):
                if d:
                    removeit(d)
                return 42

            def g(d):
                return f(d)
        """
        with self.in_module(codestr) as mod:
            g = mod["g"]
            f = mod["f"]
            import weakref

            wr = weakref.ref(f, lambda *args: self.assertEqual(i, -1))
            del f
            for i in range(100):
                g(False)
            i = -1
            self.assertEqual(g(True), 42)
            i = 0
            self.assertEqual(g(True), None)

    def test_patch_function_unwatchable_dict(self):
        codestr = """
            def f():
                return 42

            def g():
                return f()
        """
        with self.in_module(codestr) as mod:
            g = mod["g"]
            for i in range(100):
                g()
            with patch(
                f"{mod['__name__']}.f",
                autospec=True,
                return_value=100,
            ) as p:
                mod[42] = 1
                self.assertEqual(g(), 100)

    def test_patch_function_deleted_func(self):
        codestr = """
            def f():
                return 42

            def g():
                return f()
        """
        with self.in_module(codestr) as mod:
            g = mod["g"]
            for i in range(100):
                g()
            del mod["f"]
            with self.assertRaisesRegex(
                TypeError,
                re.escape(
                    "bad name provided for class loader, "
                    + f"'f' doesn't exist in ('{mod['__name__']}', 'f')"
                ),
            ):
                g()

    def test_patch_static_function(self):
        codestr = """
            class C:
                @staticmethod
                def f():
                    return 42

            def g():
                return C.f()
        """
        with self.in_module(codestr) as mod:
            g = mod["g"]
            for i in range(100):
                self.assertEqual(g(), 42)
            with patch(f"{mod['__name__']}.C.f", autospec=True, return_value=100) as p:
                self.assertEqual(g(), 100)

    def test_patch_static_function_non_autospec(self):
        codestr = """
            class C:
                @staticmethod
                def f():
                    return 42

            def g():
                return C.f()
        """
        with self.in_module(codestr) as mod:
            g = mod["g"]
            for i in range(100):
                g()
            with patch(f"{mod['__name__']}.C.f", return_value=100) as p:
                self.assertEqual(g(), 100)

    def test_patch_primitive_ret_type(self):
        for type_name, value, patched in [
            ("cbool", True, False),
            ("cbool", False, True),
            ("int8", 0, 1),
            ("int16", 0, 1),
            ("int32", 0, 1),
            ("int64", 0, 1),
            ("uint8", 0, 1),
            ("uint16", 0, 1),
            ("uint32", 0, 1),
            ("uint64", 0, 1),
        ]:
            with self.subTest(type_name=type, value=value, patched=patched):
                codestr = f"""
                    from __static__ import {type_name}, box
                    class C:
                        def f(self) -> {type_name}:
                            return {value!r}

                    def g():
                        return box(C().f())
                """
                with self.in_module(codestr) as mod:
                    g = mod["g"]
                    for i in range(100):
                        self.assertEqual(g(), value)
                    with patch(f"{mod['__name__']}.C.f", return_value=patched) as p:
                        self.assertEqual(g(), patched)

    def test_patch_primitive_ret_type_overflow(self):
        codestr = f"""
            from __static__ import int8, box
            class C:
                def f(self) -> int8:
                    return 1

            def g():
                return box(C().f())
        """
        with self.in_module(codestr) as mod:
            g = mod["g"]
            for i in range(100):
                self.assertEqual(g(), 1)
            with patch(f"{mod['__name__']}.C.f", return_value=256) as p:
                with self.assertRaisesRegex(
                    OverflowError,
                    "unexpected return type from C.f, expected "
                    "int8, got out-of-range int \\(256\\)",
                ):
                    g()

    def test_invoke_strict_module_patching(self):
        codestr = """
            def f():
                return 42

            def g():
                return f()
        """
        with self.in_strict_module(codestr, enable_patching=True) as mod:
            g = mod.g
            for i in range(100):
                self.assertEqual(g(), 42)
            self.assertInBytecode(g, "INVOKE_FUNCTION", ((mod.__name__, "f"), 0))
            mod.patch("f", lambda: 100)
            self.assertEqual(g(), 100)

    def test_invoke_patch_non_vectorcall(self):
        codestr = """
            def f():
                return 42

            def g():
                return f()
        """
        with self.in_strict_module(codestr, enable_patching=True) as mod:
            g = mod.g
            self.assertInBytecode(g, "INVOKE_FUNCTION", ((mod.__name__, "f"), 0))
            self.assertEqual(g(), 42)
            mod.patch("f", Mock(return_value=100))
            self.assertEqual(g(), 100)

    def test_patch_method(self):
        codestr = """
            class C:
                def f(self):
                    pass

            def g():
                return C().f()
        """
        with self.in_module(codestr) as mod:
            g = mod["g"]
            C = mod["C"]
            orig = C.f
            C.f = lambda *args: args
            for i in range(100):
                v = g()
                self.assertEqual(type(v), tuple)
                self.assertEqual(type(v[0]), C)
            C.f = orig
            self.assertEqual(g(), None)

    def test_patch_method_ret_none_error(self):
        codestr = """
            class C:
                def f(self) -> None:
                    pass

            def g():
                return C().f()
        """
        with self.in_module(codestr) as mod:
            g = mod["g"]
            C = mod["C"]
            C.f = lambda *args: args
            with self.assertRaisesRegex(
                TypeError,
                "unexpected return type from C.f, expected NoneType, got tuple",
            ):
                v = g()

    def test_patch_method_ret_none(self):
        codestr = """
            class C:
                def f(self) -> None:
                    pass

            def g():
                return C().f()
        """
        with self.in_module(codestr) as mod:
            g = mod["g"]
            C = mod["C"]
            C.f = lambda *args: None
            self.assertEqual(g(), None)

    def test_patch_method_bad_ret(self):
        codestr = """
            class C:
                def f(self) -> int:
                    return 42

            def g():
                return C().f()
        """
        with self.in_module(codestr) as mod:
            g = mod["g"]
            C = mod["C"]
            C.f = lambda *args: "abc"
            with self.assertRaisesRegex(
                TypeError, "unexpected return type from C.f, expected int, got str"
            ):
                v = g()