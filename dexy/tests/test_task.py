from dexy.exceptions import *
from dexy.runner import Runner
from dexy.task import Task
from dexy.tests.utils import divert_stdout
from dexy.tests.utils import temprun
from nose.tools import raises

def test_init():
    task = Task("key")
    assert isinstance(task.args, dict)
    assert isinstance(task.children, list)
    assert task.key == "key"

    assert hasattr(task, 'pre')
    assert hasattr(task, 'post')
    assert hasattr(task.pre, "__call__")
    assert hasattr(task.post, "__call__")

def test_kwargs():
    task = Task("key", foo="bar", abc="def")
    assert task.args['foo'] == 'bar'
    assert task.args['abc'] == 'def'

@raises(UnexpectedState)
def test_invalid_state():
    task = Task("key")
    task.state = "invalid"
    for t in task:
        t()

@raises(InvalidStateTransition)
def test_invalid_transition():
    task = Task('key')
    task.transition('complete')

def test_set_log():
    task = Task("key")
    assert not hasattr(task, 'log')
    task.set_log()
    assert hasattr(task, 'log')
    assert hasattr(task, 'logstream')
    task.log.debug("please write me to log")
    assert "please write me to log" in task.logstream.getvalue()

def test_circular():
    runner = Runner()
    d1 = Task("1",runner=runner)
    d2 = Task("2",runner=runner)

    d1.children.append(d2)
    d2.children.append(d1)

    try:
        for t in d1:
            t()
        assert False
    except CircularDependency:
        assert True

@raises(CircularDependency)
def test_circular_4_docs():
    runner = Runner()
    d1 = Task("1", runner=runner)
    d2 = Task("2", runner=runner)
    d3 = Task("3", runner=runner)
    d4 = Task("4", runner=runner)

    d1.children.append(d2)
    d2.children.append(d3)
    d3.children.append(d4)
    d4.children.append(d1)

    for t in d1:
        t()

class SubclassTask(Task):
    def pre(self, *args, **kw):
        print "pre '%s'" % self.key,

    def run(self, *args, **kw):
        print "run '%s'" % self.key,

    def post(self, *args, **kw):
        print "post '%s'" % self.key,

def test_run_incorrectly():
    with divert_stdout() as stdout:
        with temprun() as runner:
            for demotaskinstance in (SubclassTask("demo", runner=runner),):
                demotaskinstance()
        assert "run 'demo'" == stdout.getvalue()

def test_run_demo_single():
    with divert_stdout() as stdout:
        runner = Runner()
        doc = SubclassTask("demo", runner=runner)

        runner.docs = [doc]
        runner.run()

        assert "pre 'demo' run 'demo' post 'demo'" == stdout.getvalue()

def test_run_demo_parent_child():
    with divert_stdout() as stdout:
        runner = Runner()
        doc = SubclassTask(
                    "parent",
                    SubclassTask("child", runner=runner),
                    runner=runner
                )

        runner.docs = [doc]
        runner.run()

        assert "pre 'parent' pre 'child' run 'child' post 'child' run 'parent' post 'parent'" == stdout.getvalue()

def test_dependencies_only_run_once():
    with divert_stdout() as stdout:
        runner = Runner()

        t1 = SubclassTask("1", runner=runner)
        t2 = SubclassTask("2", t1, runner=runner)
        t3 = SubclassTask("3", t1, runner=runner)

        runner.docs = [t1, t2, t3]
        runner.run()

        assert stdout.getvalue() == "pre '1' run '1' post '1' pre '2' run '2' post '2' pre '3' run '3' post '3'"

        assert len(t1.completed_children) == 0
        assert t1 in t2.completed_children.values()
        assert t1 in t3.completed_children.values()

class AddNewSubtask(Task):
    def pre(self):
        new_task = SubclassTask("new", runner=self.runner)
        self.children.append(new_task)

def test_add_new_subtask():
    with divert_stdout() as stdout:
        runner = Runner()
        t1 = AddNewSubtask("parent", runner=runner)

        runner.docs = [t1]
        runner.run()

        assert stdout.getvalue() == "pre 'new' run 'new' post 'new'"

def test_completed_children():
    with temprun() as runner:
        with divert_stdout() as stdout:
            grandchild_task = SubclassTask("grandchild", runner=runner)
            child_task = SubclassTask("child", grandchild_task, runner=runner)
            parent_task = SubclassTask("parent", child_task, runner=runner)

            runner.docs = [parent_task]
            runner.run()

            assert stdout.getvalue() == "pre 'parent' pre 'child' pre 'grandchild' run 'grandchild' post 'grandchild' run 'child' post 'child' run 'parent' post 'parent'"

    assert "SubclassTask:grandchild" in parent_task.completed_children.keys()
    assert "SubclassTask:child" in parent_task.completed_children.keys()

    assert "SubclassTask:grandchild" in child_task.completed_children.keys()

    assert len(grandchild_task.completed_children) == 0
