Contributing
============

If you would like to contribute to the project, there's a few things you should know, to assist your development efforts and make the pull request workflow easier on everyone

Running locally
---------------

To test your changes locally, we recommend pip installing the local changes - this ensures the build process is also working fine.
While in the top level directory, you can run

.. code-block:: bash

    pip install -e  ./

or

.. code-block:: bash
    
    python setup.py develop

To install the project. This creates a .pth link from your python installation to your ev3sim directory. This means any changes made will immediately take effect. Note that this will remove your existing install of stable ev3sim (if installed via pip), so be aware of this.

Linting code
------------

Pull requests are linted with `black`_. To run black locally to fix any formatting errors you've made, run the following:

.. code-block:: bash

    black --config pyproject.toml .

.. _black: https://github.com/psf/black
