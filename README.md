# Atomic Tracer

A language agnostic Atom package for tracing variables inline!

It shows you where a variable was declared and its value at each line thereafter:

![simple_example](https://raw.githubusercontent.com/OmarShehata/atom-tracer/master/_images/tracer_simple.gif)

If a line of code is executed more than once, you can see all the values it had in a list:

![for_example](https://raw.githubusercontent.com/OmarShehata/atom-tracer/master/_images/tracer_for.gif)

It also works on function arguments:

![funcexample](https://raw.githubusercontent.com/OmarShehata/atom-tracer/master/_images/tracer_func.gif)

Currently only Python is supported, but you can help out and add more languages without having to touch any of the core plugin code!

# Installation

This package depends on [Ink](https://github.com/JunoLab/atom-ink), so install that one first. 

Then install the tracer from your Atom settings, or through `apm`:

```
apm install atom-tracer
```

# Usage

Once installed, you can hold Alt and double click on a variable to trace it. Double click anywhere in the file to clear the results.

Click on the result box to copy its contents.

You can also select a variable, right click and click on "Trace variable" in the context menu.

# What is this for?

This is not a very sophisticated debugger (for one thing, you can't trace anything that requires user input). It's intended to be used as a teaching tool.

I created this because I think learning to reason about code and debug it is an important skill, and not having an easy way to see the flow of execution hinders that. I wanted to have a tool that made it transparent to the student what was happening throughout the lifetime of a variable in an effort to check their understanding.

# How does it work?

It parses the abstract syntax tree to find where the variable is declared and what its scope is, and then injects print statements into the file, runs it, captures the output, and displays it inline.

If you want more details, see this [page](HowItWorks.md)!

This is built on top of the awesome [Ink](https://github.com/JunoLab/atom-ink) package!

# Contributions are very welcome!

There are two ways to contribute. The easiest way is to use the plugin on your own code and see if it works. If you're getting an error on a piece of code, or it's just not doing what you expect, please open an issue and paste your code snippet to recreate it! Or just generally suggest features/ideas!

The other way is to create a new language! We want to support as many languages as possible. Check out this [guide](HowItWorks.md) on how the tracer works to extend it.
