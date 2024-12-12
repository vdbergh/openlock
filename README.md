# openlock

A locking library not depending on inter-process locking primitives in the OS.

Consider a simple situation where multiple processes with the same working directory are trying to access a shared resource.

Create the lock.

```python
l = FileLock()
```

Acquire the lock.

```python
l.acquire()
```

Release the lock.

```python
l.release()
```

Alternatively we may use the context manager protocol.

```python
  with FileLock():
    ...
```

That's it!

For comprehensive documentation about `openlock` see [https://www.cantate.be/openlock](https://www.cantate.be/openlock) (canonical reference) or [https://openlock.readthedocs.io](https://openlock.readthedocs.io).
