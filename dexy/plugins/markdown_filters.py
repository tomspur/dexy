from dexy.filter import Filter
import dexy.exceptions
import logging
import markdown
import json

class MarkdownFilter(Filter):
    """
    Runs a Markdown processor to convert markdown to HTML.

    Markdown extensions can be enabled in your config:
    http://packages.python.org/Markdown/extensions/index.html
    """
    INPUT_EXTENSIONS = ['.*']
    OUTPUT_EXTENSIONS = ['.html']
    ALIASES = ['markdown']
    DEFAULT_EXTENSIONS = {'toc' : {}}

    def process_text(self, input_text):
        markdown_logger = logging.getLogger('MARKDOWN')
        markdown_logger.addHandler(self.log.handlers[-1])

        if len(self.args()) > 0:
            extensions = self.args().keys()
            extension_configs = self.args()
        else:
            extensions = self.DEFAULT_EXTENSIONS.keys()
            extension_configs = self.DEFAULT_EXTENSIONS

        dbg = "Initializing Markdown with extensions: %s and extension configs: %s"
        self.log.debug(dbg % (json.dumps(extensions), json.dumps(extension_configs)))

        try:
            md = markdown.Markdown(
                    extensions=extensions,
                    extension_configs=extension_configs)
        except ValueError as e:
            print e
            if "markdown.Extension" in e.message:
                raise dexy.exceptions.UserFeedback("Something is wrong with markdown extensions specified. Please check dexy log flie.")
            else:
                raise e

        return md.convert(input_text)
