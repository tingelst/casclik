"""Skill specification and tools for specification.

This module contains the SkillSpecification class, and tools for the
skill specification. It is used to contain a bunch of constraints, and
it is used to define controllers (see controllers file). The
SkillSpecification class is inspired by the eTaSL specification files
where a lua file is used to define a "task context".

Ideas:
    1. Should constraints of equal priority be automatically
combined?
    2. Should we look into sanity checks on rank and such?
    3. Should we make some sort of support for input_vel_var?
Todo:
    * Add sanity checks to setters of ###_var's
    * Add sanity checks to setter of constraints
"""
import casadi as cs
from casclik.constraints import EqualityConstraint, SetConstraint, VelocityEqualityConstraint, VelocitySetConstraint
import sys


class SkillSpecification(object):
    """Specification of a skill to be executed on the robot.

    Args:
        label (str): Name of the skill
        time_var (cs.MX.sym): symbol for time
        robot_var (cs.MX.sym): Controllable robot variables
        virtual_var (cs.MX.sym): Internal virtual variables
        input_var (cs.MX.sym): Input variables, jacobian not calculated
    """
    _constraints = []
    _virtual_var = None
    _input_var = None

    def __init__(self, label, time_var,
                 robot_var,
                 robot_vel_var=None,
                 virtual_var=None,
                 virtual_vel_var=None,
                 input_var=None,
                 constraints=[]):
        self.label = label
        self.time_var = time_var
        self.robot_var = robot_var
        self.robot_vel_var = robot_vel_var
        self.virtual_var = virtual_var
        self.virtual_vel_var = virtual_vel_var
        self.input_var = input_var
        self.constraints = constraints

    @property
    def robot_var(self):
        """Get or set the robot_var. Setting the robot_var also sets
        n_robot_var."""
        return self._robot_var

    @robot_var.setter
    def robot_var(self, var):
        self._robot_var = var
        if var is not None:
            self.n_robot_var = var.size()[0]
        else:
            self.n_robot_var = 0

    @property
    def robot_vel_var(self):
        """Get or set the robot_vel_var. The robot_vel_var must be the same
        dimensions as robot_var"""
        return self._robot_vel_var

    @robot_vel_var.setter
    def robot_vel_var(self, var):
        if var is None:
            self._robot_vel_var = cs.MX.sym("robot_vel_var", self.n_robot_var)
        else:
            if not isinstance(var, cs.MX):
                raise TypeError("robot_vel_var must be cs.MX.sym.")
            if var.size() != self.robot_var.size():
                raise ValueError("robot_var and robot_vel_var must have the"
                                 + " same dimensions")
            self._robot_vel_var = var

    @property
    def virtual_var(self):
        """Get or set the virtual_var. Setting the virtual_var also sets
        n_virtual_var."""
        return self._virtual_var

    @virtual_var.setter
    def virtual_var(self, var):
        self._virtual_var = var
        if var is not None:
            self.n_virtual_var = var.size()[0]
        else:
            self.n_virtual_var = 0
        self._check_var_existence()

    @property
    def virtual_vel_var(self):
        return self._virtual_vel_var

    @virtual_vel_var.setter
    def virtual_vel_var(self, var):
        if var is None:
            self._virtual_vel_var = cs.MX.sym("virtual_vel_var",
                                              self.n_virtual_var)
        else:
            if not isinstance(var, cs.MX):
                raise TypeError("virtual_vel_var must be cs.MX.sym.")
            if var.size() != self.virtual_var.size():
                raise ValueError("virtual_vel_var and virtual_var must have"
                                 + " the same dimensions")
            self._virtual_vel_var = var

    @property
    def input_var(self):
        """Get or set the input_var. Setting the input_var also sets
        n_input_var."""
        return self._input_var

    @input_var.setter
    def input_var(self, var):
        self._input_var = var
        if var is not None:
            self.n_input_var = var.size()[0]
        else:
            self.n_input_var = 0
        self._check_var_existence()

    @property
    def constraints(self):
        """Get or set the constraints list. The list is automatically sorted
        on cnstr.priority, and n_slack_var and slack_var are created based on
        the number and size of the soft constraints."""
        return self._constraints

    @constraints.setter
    def constraints(self, cnstr_list):
        self._constraints = sorted(cnstr_list,
                                   key=lambda cnstr: cnstr.priority)
        n_slack_var = 0
        for cnstr in self._constraints:
            if cnstr.constraint_type == "soft":
                n_slack_var += cnstr.expression.size()[0]
        self.n_slack_var = n_slack_var
        if n_slack_var != 0:
            self.slack_var = cs.MX.sym("slack_var", n_slack_var)
        else:
            self.slack_var = None
        self._check_var_existence()

    def _check_var_existence(self):
        """Internal function to set _has_virtual, and _has_input.
        Loops over constraints to see if the derivatives are non-zero."""
        self._has_virtual = False
        if self.virtual_var is not None:
            virtual_var = self.virtual_var
            for cnstr in self.constraints:
                if cs.jacobian(cnstr.expression, virtual_var).nnz() > 0:
                    self._has_virtual = True
                if hasattr(cnstr, "target"):
                    if isinstance(cnstr.target, cs.MX):
                        if cs.jacobian(cnstr.target, virtual_var).nnz() > 0:
                            self._has_virtual = True
                if hasattr(cnstr, "set_min"):
                    if isinstance(cnstr.set_min, cs.MX):
                        if cs.jacobian(cnstr.set_min, virtual_var).nnz() > 0:
                            self._has_virtual = True
                if hasattr(cnstr, "set_max"):
                    if isinstance(cnstr.set_max, cs.MX):
                        if cs.jacobian(cnstr.set_max, virtual_var).nnz() > 0:
                            self._has_virtual = True
                if hasattr(cnstr, "gain"):
                    if isinstance(cnstr.gain, cs.MX):
                        if cs.jacobian(cnstr.gain, virtual_var).nnz() > 0:
                            self._has_virtual = True
        self._has_input = False
        if self.input_var is not None:
            input_var = self.input_var
            for cnstr in self.constraints:
                if cs.jacobian(cnstr.expression, input_var).nnz() > 0:
                    self._has_input = True
                if hasattr(cnstr, "target"):
                    if isinstance(cnstr.target, cs.MX):
                        if cs.jacobian(cnstr.target, input_var).nnz() > 0:
                            self._has_input = True
                if hasattr(cnstr, "set_min"):
                    if isinstance(cnstr.set_min, cs.MX):
                        if cs.jacobian(cnstr.set_min, input_var).nnz() > 0:
                            self._has_input = True
                if hasattr(cnstr, "set_max"):
                    if isinstance(cnstr.set_max, cs.MX):
                        if cs.jacobian(cnstr.set_max, input_var).nnz() > 0:
                            self._has_input = True
                if hasattr(cnstr, "gain"):
                    if isinstance(cnstr.gain, cs.MX):
                        if cs.jacobian(cnstr.gain, input_var).nnz() > 0:
                            self._has_input = True

    def print_constraints(self):
        """Prints information about the constraints in the skill."""
        sys.stdout.write("SkillSpecification: "+self.label+"\n")
        for cnstr_id, cnstr in enumerate(self.constraints):
            sys.stdout.write("#"+str(cnstr_id)+": "+cnstr.label+"\n")
        sys.stdout.write("Has virtual var: "+str(self._has_virtual)+"\n")
        sys.stdout.write("Has input var: "+str(self._has_input)+"\n")
        count_dict = self.count_constraints()
        sys.stdout.write("N constraints: "+str(count_dict["all"])+"\n")
        sys.stdout.write("N equality:\n")
        sys.stdout.write("\tPos:"+str(count_dict["equality"]))
        sys.stdout.write("\tVel:"+str(count_dict["velocity_equality"])+"\n")
        sys.stdout.write("N set:\n")
        sys.stdout.write("\tPos:"+str(count_dict["set"]))
        sys.stdout.write("\tVel:"+str(count_dict["velocity_set"])+"\n")
        sys.stdout.flush()

    def count_constraints(self):
        """Count constraints in skill.
        Returns:
            dict: {"all", "equality", "set", "hard","soft"}
        """
        n_eq = 0
        n_set = 0
        n_vel_eq = 0
        n_vel_set = 0
        n_all = len(self.constraints)
        n_hard = 0
        n_soft = 0
        for cnstr in self.constraints:
            if cnstr.constraint_type == "hard":
                n_hard += 1
            elif cnstr.constraint_type == "soft":
                n_soft += 1
            if isinstance(cnstr, EqualityConstraint):
                n_eq += 1
            elif isinstance(cnstr, SetConstraint):
                n_set += 1
            elif isinstance(cnstr, VelocityEqualityConstraint):
                n_vel_eq += 1
            elif isinstance(cnstr, VelocitySetConstraint):
                n_vel_set += 1
        return {"all": n_all,
                "equality": n_eq,
                "velocity_equality": n_vel_eq,
                "set": n_set,
                "velocity_set": n_vel_set,
                "hard": n_hard,
                "soft": n_soft}
