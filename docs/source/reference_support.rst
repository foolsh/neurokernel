.. -*- rst -*-

Support Classes and Functions
=============================

Path-Like Port Identifier Handling
----------------------------------
.. currentmodule:: neurokernel.plsel
.. autosummary::
   :toctree: generated/
   :nosignatures:

   PathLikeSelector
   PortMapper

XML Tools
---------
.. currentmodule:: neurokernel.neuroml.utils
.. autosummary::
   :toctree: generated/
   :nosignatures:

   graph_to_nml_module
   graph_to_nml_pattern
   load
   nml_pattern_to_graph
   nml_module_to_graph
   write

Context Managers
----------------
.. currentmodule:: neurokernel.ctx_managers
.. autosummary::
   :toctree: generated/
   :nosignatures:

   ExceptionOnSignal
   IgnoreKeyboardInterrupt
   IgnoreSignal
   OnKeyboardInterrupt
   TryExceptionOnSignal

Communication Tools
-------------------
.. currentmodule:: neurokernel.tools.comm
.. autosummary::
   :toctree: generated/
   :nosignatures:

   get_random_port
   is_poll_in
   ZMQOutput

.. reenable after these are rewritten to use the new Interface/Pattern classes
   Graph Tools
   -----------
   .. currentmodule:: neurokernel.tools.graph
   .. autosummary::
      :toctree: generated/
      :nosignatures:

      graph_to_df

Visualization Tools
-------------------
.. currentmodule:: neurokernel.tools.plot
.. autosummary::
   :toctree: generated/
   :nosignatures:

   imdisp
   show_pydot
   show_pygraphviz

Other
-----
.. currentmodule:: neurokernel.mixins
.. autosummary::
    :toctree: generated/
    :nosignatures:

   LoggerMixin

.. currentmodule:: neurokernel.tools.misc
.. autosummary::
   :toctree: generated/
   :nosignatures:

   catch_exception
   rand_bin_matrix
