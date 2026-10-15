import pickle
import io

class InspectUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        print(f"find_class: module='{module}', name='{name}'")
        try:
            return super().find_class(module, name)
        except Exception as e:
            print(f"  -> failed: {e}")
            import importlib
            try:
                mod = importlib.import_module(module)
                return getattr(mod, name)
            except Exception as e2:
                print(f"  -> importlib failed: {e2}")
                class Dummy:
                    pass
                return Dummy

with open('models/adaptive_quiz_model.pkl', 'rb') as f:
    unpickler = InspectUnpickler(f)
    try:
        obj = unpickler.load()
        print("Loaded object:", type(obj), obj)
        print("Dict:", getattr(obj, '__dict__', {}))
    except Exception as e:
        print("Final error:", e)
