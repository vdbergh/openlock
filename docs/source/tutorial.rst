Getting started
===============

Installation
------------

`openlock` is available via pip:

.. code-block:: console

   $ pip install openlock


   
Tutorial
--------

Create the lock.

.. code-block:: python

  l = FileLock()

Acquire the lock.

.. code-block:: python

  l.acquire()

Release the lock.

.. code-block:: python

  l.release()

Using the context manager protocol.

.. code-block:: python

  with FileLock():
    ...



