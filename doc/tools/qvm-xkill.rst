=========
qvm-xkill
=========

NAME
====
qvm-xkill - kill a misbehaving qubes-guid

SYNOPSIS
========
| qvm-xkill

DESCRIPTION
===========
qvm-xkill allows you to kill a qubes-guid process simply by clicking on one of its windows.
Clicking on a non-qubes-guid window has no effect and may be used to cancel selection.

qvm-xkill is useful in the event some errant VM is performing a GUI denial-of-service attack.
A VM may attempt to prevent you from interacting with your computer, e.g. by rapidly creating and destroying lots of very large windows which obscure other things (like qubes-manager) and steal focus.
You may gracefully recover from such a situation through the use of ``qvm-run --pause --all`` and ``qvm-xkill`` bound to keyboard shortcuts.

``qvm-run --pause --all`` will pause all VMs, preventing the DoSing VM from taking any more actions which restrict your ability to interact with Dom0.

qvm-xkill has the additional advantage that it allows you to easily kill the correct qubes-guid in the event the offending VM is using borderless windows, which may make it more difficult to correctly identify the originating VM.
One example of when this may occur is having many active DispVMs all with red borders, only one of which is performing a GUI DoS.

AUTHORS
=======
| Jean-Philippe Ouellet <jpo at vt dot edu>
| Rusty Bird <rustybird at openmailbox dot org>
