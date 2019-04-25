# Contributions

PyGOP is open for contributions. Especially if you are developing GOP-based algorithms and would like to catch public attention or integrate your algorithm to our codebase to enable reproducible research, you are welcome! In addition, new features, documentations, tests or bug reports are also welcome. Following is the guide to contribute to PyGOP:


## Bug Report


If you have determined that your code doesn't work and it comes from PyGOP, please follow the following step to report a bug.

1. Make sure your code is up-to-date with our current code on the master branch.

2. Make sure to check the [issue section](https://github.com/viebboy/PyGOP/issues) before filing an issue on our github project. The bug might already be reported.

3. Create an issue in [issue section](https://github.com/viebboy/PyGOP/issues). Give detailed description of your system configuration: What OS you are using? What is the python version? What is the PyGOP version? What is your computation device (cpu/gpu)? If you are using GPU, what is the model of GPU and the version of CUDA? In addition, make sure to include a complete example which we can use to trigger the bug.

4. If you know how to fix the bug, please make a request to contribute!

## Pull Request


If you want to contribute to our codebase, please send an email to viebboy@gmail.com to with subject "PYGOP DEVELOPMENT" to discuss your plan which should include the description of the contribution (bug fix, interface improvement, new feature, new test or documentation) and potential interface (for code contribution). Once we reach the agreement on how to proceed, you can

1. Fork [PyGOP on github](https://github.com/viebboy/PyGOP/)

2. Clone your fork to local machine

3. Inside the top level project directory, install the project for development purpose::

    pip install -e .

4. Make a new branch for development

5. Hook your Travis CI to your development branch to enable continuous testing

6. Write code in the development branch

7. Write unit tests in tests/ and run pytest to test your code locally

8. Write documentation in docs/

9. Make a Pull Request [here](https://github.com/viebboy/PyGOP/pulls)

