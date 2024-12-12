Getting started
===============

Installation
------------

`openlock` is available via pip:

.. code-block:: console

   $ pip install openlock


   
Tutorial
--------

For this tutorial we consider a simple situation where multiple processes with the same working directory are trying to access a shared resource.

Create the lock.

.. code-block:: python

  l = FileLock()

Acquire the lock.

.. code-block:: python

  l.acquire()

Release the lock.

.. code-block:: python

  l.release()

Alternatively we may use the context manager protocol.

.. code-block:: python

  with FileLock():
    ...

That's it!



