Guppy Libraries Documentation
#############################

An introductory tale into how Guppy libraries (are supposed to) work, how to write them, and how to use them.

.. note::
   This page concerns Guppy libraries usage for independently compiling a set of functions to a Hugr package, which can
   be independently distributed and e.g. cached for optimization purposes. If you are just looking to open source your
   Guppy code, the standard packaging mechanisms of Python suffice, and you can ignore this page.

..
  TODO: Mark parts that are in progress as such!

- Foreword
- Defining a Guppy library

  - Simple functions as interface
  - What is supported, what is not
  - ``guppy.library`` call and its arguments
  - Defining headers to program against

- Compiling the library, and what to do with the Hugr package

- User Program

  - Programming and compiling against the headers
  - Oh no, its not a runnable Hugr yet (but still a valid one)

- Providing the library Hugr package to the user program executor

  - This is the most open / underspecified part
  - Should be able to do this manually via ``hugr-py``
  - But also via simply passing more things to selene
  - Mention auto-discovery functions
