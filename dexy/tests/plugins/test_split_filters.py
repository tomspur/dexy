from dexy.tests.utils import temprun
from dexy.doc import Doc

def test_split_html_filter():
    with temprun() as runner:
        contents="""
        <p>This is at the top.</p>
        <!-- split "a-page" -->
        some content on a page
        <!-- split "another-page" -->
        some content on another page
        <!-- endsplit -->
        bottom
        """

        doc = Doc("example.html|splithtml", contents=contents, runner=runner)
        runner.docs = [doc]
        runner.run()

        assert doc.children[2].key == "a-page.html"
        assert doc.children[3].key == "another-page.html"

        od = doc.output().data()

        assert "<p>This is at the top.</p>" in od
        assert '<a href="a-page.html">' in od
        assert '<a href="another-page.html">' in od
        assert "bottom" in od

        assert "<p>This is at the top.</p>" in doc.children[2].output().data()
        assert "some content on a page" in doc.children[2].output().data()
        assert "bottom" in doc.children[2].output().data()

        assert "<p>This is at the top.</p>" in doc.children[3].output().data()
        assert "some content on another page" in doc.children[3].output().data()
        assert "bottom" in doc.children[3].output().data()

def test_split_html_additional_filters():
    with temprun() as runner:
        contents="""
        <p>This is at the top.</p>
        <!-- split "a-page" -->
        some content on a page
        <!-- split "another-page" -->
        some content on another page
        <!-- endsplit -->
        bottom
        """

        doc = Doc("example.html|splithtml",
                contents=contents,
                splithtml = { "additional_doc_filters" : "processtext" },
                runner=runner
              )
        runner.docs = [doc]
        runner.run()

        assert doc.children[2].key == "a-page.html|processtext"
        assert doc.children[3].key == "another-page.html|processtext"

        od = doc.output().data()
        assert "<p>This is at the top.</p>" in od
        assert '<a href="a-page.html">' in od
        assert '<a href="another-page.html">' in od
        assert "bottom" in od

        assert "<p>This is at the top.</p>" in doc.children[2].output().data()
        assert "some content on a page" in doc.children[2].output().data()
        assert "bottom" in doc.children[2].output().data()
        assert "Dexy processed the text" in doc.children[2].output().data()

        assert "<p>This is at the top.</p>" in doc.children[3].output().data()
        assert "some content on another page" in doc.children[3].output().data()
        assert "bottom" in doc.children[3].output().data()
        assert "Dexy processed the text" in doc.children[3].output().data()
