from dexy.filter import Filter
from idiopidae.runtime import Composer
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.formatters.latex import LatexFormatter
from pygments.lexers.agile import PythonLexer
import idiopidae.parser
import inspect
import json
import nose
import os
import pkgutil
import shutil
import subprocess
import sys

"""
Filters that parse and process various language's documentation systems to make
this information available in Dexy documents. Filters work by processing a
config file that specifies which libraries should be processed. These filters
work for languages where documentation can be generated by referencing
installed libraries, rather than needing source code.
"""

class PythonTestFilter(Filter):
    """
    Runs the tests in the specified module(s) (which must be installed on the
    system) and returns a key-value store with test results, source code and
    html and latex highlighted source code.
    """
    ALIASES = ['pytest']
    INPUT_EXTENSIONS = [".txt"]
    OUTPUT_EXTENSIONS = ['.json']
    LEXER = PythonLexer()
    LATEX_FORMATTER = LatexFormatter()
    HTML_FORMATTER = HtmlFormatter(lineanchors="pytest")

    # TODO some way to ensure tests logs get written elsewhere, like to the artifact output, they are going to main log for now - very confusing

    def process(self):
        self.artifact.setup_kv_storage()

        loader = nose.loader.TestLoader()
        for module_name in self.artifact.input_text().split():
            self.log.debug("Starting to process module '%s'" % module_name)
            tests = loader.loadTestsFromName(module_name)
            self.log.debug("Loaded tests.")
            for test in tests:
                self.log.debug("Running test suite %s" % test)
                test_passed = nose.core.run(suite=test, argv=['nosetests'])
                self.log.debug("Passed: %s" % test_passed)
                for x in dir(test.context):
                    xx = test.context.__dict__[x]
                    if inspect.ismethod(xx) or inspect.isfunction(xx):
                        test_context_name = test.context.__name__
                        qualified_test_name = "%s.%s" % (test_context_name, xx.__name__)

                        source = inspect.getsource(xx.__code__)
                        html_source = highlight(source, self.LEXER, self.HTML_FORMATTER)
                        latex_source = highlight(source, self.LEXER, self.LATEX_FORMATTER)

                        if test_passed:
                            html_result = """ <div class="test-passed"> %s PASSED </div> """ % qualified_test_name
                        else:
                            html_result = """ <div class="test-failed"> %s FAILED </div> """ % qualified_test_name

                        self.artifact.output_data.append("%s:source" % qualified_test_name, source)
                        self.artifact.output_data.append("%s:html-source" % qualified_test_name, html_source)
                        self.artifact.output_data.append("%s:latex-source" % qualified_test_name, latex_source)
                        self.artifact.output_data.append("%s:test-passed" % qualified_test_name, test_passed)
                        self.artifact.output_data.append("%s:html-result" % qualified_test_name, html_result)
                        self.artifact.output_data.append("%s:html-source+result" % qualified_test_name, "%s\n%s" % (html_source, html_result))

        self.artifact._storage.save()

class PythonDocumentationFilter(Filter):
    ALIASES = ["pydoc"]
    INPUT_EXTENSIONS = [".txt"]
    OUTPUT_EXTENSIONS = ['.json']
    COMPOSER = Composer()
    OUTPUT_DATA_TYPE = 'keyvalue'
    LEXER = PythonLexer()
    LATEX_FORMATTER = LatexFormatter()
    HTML_FORMATTER = HtmlFormatter(lineanchors="pydoc")

    def fetch_item_content(self, key, item):
        is_method = inspect.ismethod(item)
        is_function = inspect.isfunction(item)
        if is_method or is_function:
            # Get source code
            try:
                source = inspect.getsource(item)
            except IOError as e:
                source = ""
            # Process any idiopidae tags
            builder = idiopidae.parser.parse('Document', source + "\n\0")

            sections = {}
            for i, s in enumerate(builder.sections):
                lines = builder.statements[i]['lines']
                sections[s] = "\n".join(l[1] for l in builder.statements[i]['lines'])

            if isinstance(sections, dict):
                if len(sections.keys()) > 1 or sections.keys()[0] != '1':
                    for section_name, section_content in sections.iteritems():
                        self.add_source_for_key("%s:%s" % (key, section_name), section_content)
                else:
                    self.add_source_for_key(key, sections['1'])
            else:
                self.add_source_for_key(key, sections)

            self.artifact.output_data.append("%s:doc" % key, inspect.getdoc(item))
            self.artifact.output_data.append("%s:comments" % key, inspect.getcomments(item))

        else: # not a function or a method
            try:
                # If this can be JSON-serialized, leave it alone...
                json.dumps(item)
                self.add_source_for_key(key, item)
            except TypeError:
                # ... if it can't, convert it to a string to avoid problems.
                self.add_source_for_key(key, str(item))

    def highlight_html(self, source):
        return highlight(source, self.LEXER, self.HTML_FORMATTER)

    def highlight_latex(self, source):
        return highlight(source, self.LEXER, self.LATEX_FORMATTER)

    def add_source_for_key(self, key, source):
        """
        Appends source code + syntax highlighted source code to persistent store.
        """
        self.artifact.output_data.append("%s:value" % key, source)
        if not (type(source) == str or type(source) == unicode):
            source = inspect.getsource(source)
        self.artifact.output_data.append("%s:source" % key, source)
        self.artifact.output_data.append("%s:html-source" % key, self.highlight_html(source))
        self.artifact.output_data.append("%s:latex-source" % key, self.highlight_latex(source))

    def process_members(self, package_name, mod):
        """
        Process all members of the package or module passed.
        """
        name = mod.__name__

        for k, m in inspect.getmembers(mod):
            self.log.debug("in %s processing element %s" % (mod.__name__, k))
            if not inspect.isclass(m) and hasattr(m, '__module__') and m.__module__ and m.__module__.startswith(package_name):
                key = "%s.%s" % (m.__module__, k)
                self.fetch_item_content(key, m)

            elif inspect.isclass(m) and m.__module__.startswith(package_name):
                key = "%s.%s" % (mod.__name__, k)
                try:
                    item_content = inspect.getsource(m)
                    self.artifact.output_data.append("%s:doc" % key, inspect.getdoc(m))
                    self.artifact.output_data.append("%s:comments" % key, inspect.getcomments(m))
                    self.add_source_for_key(key, item_content)
                except IOError:
                    self.log.debug("can't get source for %s" % key)
                    self.add_source_for_key(key, "")

                try:
                    for ck, cm in inspect.getmembers(m):
                        key = "%s.%s.%s" % (name, k, ck)
                        self.fetch_item_content(key, cm)
                except AttributeError:
                    pass

            else:
                key = "%s.%s" % (name, k)
                self.fetch_item_content(key, m)

    def process_module(self, package_name, name):
        try:
            self.log.debug("Trying to import %s" % name)
            __import__(name)
            mod = sys.modules[name]
            self.log.debug("Success importing %s" % name)

            try:
                module_source = inspect.getsource(mod)
                json.dumps(module_source)
                self.add_source_for_key(name, inspect.getsource(mod))
            except (UnicodeDecodeError, IOError, TypeError):
                self.log.debug("Unable to load module source for %s" % name)

            self.process_members(package_name, mod)

        except (ImportError, TypeError) as e:
            self.log.debug(e)

    def process(self):
        """
        input_text should be a list of installed python libraries to document.
        """
        package_names = self.artifact.input_data.as_text().split()
        packages = [__import__(package_name) for package_name in package_names]

        for package in packages:
            self.log.debug("processing package %s" % package)
            package_name = package.__name__
            prefix = package.__name__ + "."

            self.process_members(package_name, package)

            if hasattr(package, '__path__'):
                for module_loader, name, ispkg in pkgutil.walk_packages(package.__path__, prefix=prefix):
                    self.log.debug("in package %s processing module %s" % (package_name, name))
                    if not name.endswith("__main__"):
                        self.process_module(package_name, name)
            else:
                self.process_module(package.__name__, package.__name__)

        self.artifact.output_data.save()

class RDocumentationFilter(Filter):
    """
    Can be run on a text file listing packages to be processed, or an R script
    which should define a list of package names (strings) named 'packages', the
    latter option so that you can include some R code prior to automated code
    running.
    """
    ALIASES = ["rdoc"]
    INPUT_EXTENSIONS = [".txt", ".R"]
    OUTPUT_EXTENSIONS = [".json"]

    def process(self):
        # Create a temporary directory to run R in.
        self.artifact.create_temp_dir()
        td = self.artifact.temp_dir()

        r_script_file = os.path.join(INSTALL_DIR, 'dexy', 'ext', "introspect.R")
        self.log.debug("r docs introspection script file: %s" % r_script_file)

        with open(r_script_file, "r") as f:
            r_script_contents = f.read()

        if self.artifact.input_ext == ".txt":
            # A text file containing the names of packages to process.
            package_names = self.artifact.input_text().split()
            script_start = "packages <- c(%s)" % ",".join("\"%s\"" % n for n in package_names)
        elif self.artifact.input_ext == ".R":
            script_start = self.artifact.input_text()
        else:
            raise Exception("Unexpected input file extension %s" % self.artifact.input_ext)

        script_filename = os.path.join(td, "script.R")

        data_filename = "dexy--r-doc-info%s" % self.artifact.ext

        with open(script_filename, "w") as f:
            f.write(script_start + "\n")
            f.write("""data.filename <- "%s"\n""" % data_filename)
            f.write(r_script_contents)

        command = "R CMD BATCH script.R"
        self.log.debug("About to run %s in %s" % (command, td))

        proc = subprocess.Popen(command, shell=True,
                                cwd=td,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                )
        stdout, stderr = proc.communicate()
        shutil.copyfile(os.path.join(td, data_filename), self.artifact.filepath())

