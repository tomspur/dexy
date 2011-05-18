from ansi2html import Ansi2HTMLConverter
from pynliner import Pynliner
from BeautifulSoup import BeautifulSoup

def ansi_output_to_html(ansi_text, log=None):
    converter = Ansi2HTMLConverter()
    html = converter.convert(ansi_text)

    try:
        if not log:
            print """a custom log has not been passed to dexy.utils.ansi_output_to_html,
            harmless but annoying CSS errors will appear on the console."""
        p = Pynliner(log)
    except TypeError:
        print "dexy says: please upgrade to the latest version of pynliner (e.g. easy_install -U pynliner)"
        p = Pynliner()

    p.from_string(html)
    html_with_css_inline = p.run()

    # Ansi2HTMLConverter returns a complete HTML document, we just want body
    doc = BeautifulSoup(html_with_css_inline)
    return doc.body.renderContents()

def print_string_diff(str1, str2):
    msg = ""
    for i, c1 in enumerate(str1):
        if len(str2) > i:
            c2 = str2[i]
            if c1 == c2:
                flag = ""
            else:
                flag = " <---"
            if ord(c1) > ord('a') and ord(c2) > ord('a'):
                msg = msg + "\n%5d: %s\t%s\t\t%s\t%s %s" % (i, c1, c2,
                                              ord(c1), ord(c2), flag)
            else:
                msg = msg + "\n%5d:  \t \t\t%s\t%s %s" % (i, ord(c1),
                                              ord(c2), flag)
        else:
            flag = "<---"
            msg = msg + "\n%5d:  \t \t\t%s %s" % (i, ord(c1), flag)
    return msg
