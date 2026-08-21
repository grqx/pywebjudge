document.addEventListener('DOMContentLoaded', async ()=>{
    const userCode = document.getElementById('user-code');
    const btn = document.getElementById('run');
    const evalStdin = document.getElementById('eval-stdin');
    const output = document.getElementById('output');
    const cbtns = document.querySelectorAll('.testcase button.cbtn');
    const judgeTc = document.getElementById('judge-tc');
    // we do this even if it is already set in the html
    // because some browsers save form states automatically
    btn.setAttribute('disabled', '');
    const arrEq = (a,b)=>
      a.length === b.length &&
      a.every((v, i) => v === b[i]);

    function cBtnOnClick() {
        const tcIn = this.closest('.testcase').querySelector('.tc-in');
        evalStdin.innerText = tcIn.innerText;
    }

    for (const cbtn of cbtns)
        cbtn.onclick = cBtnOnClick;

    let warned = false;
    function stderrBatch() {
        if (!warned) {
            warned = true;
            alert('writes to stderr is ignored in the judge environment. Please use stdout instead! (This warning will only show once)'); 
        }
    }
    const evalIO = {
        0: function () { return this.input.shift(); },
        1: function (l) { output.innerText += l + '\n'; },
        2: stderrBatch,
        input: null,
    };

    const judgeIO = {
        0: function () { return this.input.shift(); },
        1: function (l) { this.output.push(l); },
        2: stderrBatch,
        chk: function () {
            if (this.checkOut === null) return false;
            return arrEq(this.checkOut, this.output);
        },
        input: [],
        output: null,
        checkOut: null,
    };

    const pyodide = await loadPyodide({ jsglobals: {} });

    function setPyIO(o) {
        pyodide.setStdin({stdin: ()=>o[0]()});
        pyodide.setStdout({batched: l=>o[1](l)});
        pyodide.setStderr({batched: l=>o[2](l)});
    }
    function wrappedRun() {
        try {
            pyodide.runPython(userCode.innerText);
            return true;
        } catch (e) {
            if (e instanceof pyodide.ffi.PythonError) {
                output.innerText += e.message + '\n';
                alert('Uncaught python exception!');
                return false;
            }
            else throw e;
        }
    }

    function judge(tcId) {
        const tc = cbtns[tcId].closest('.testcase');
        const tcIn = tc.querySelector('.tc-in')?.innerText;
        const tcOut = tc.querySelector('.tc-out')?.innerText;
        judgeIO.input = tcIn ? tcIn.split(/\r?\n/) : [];
        judgeIO.output = [];
        output.innerText = '';  // for error
        judgeIO.checkOut = tcOut ? tcOut.split(/\r?\n/) : [];
        if (!wrappedRun()) return false;
        return judgeIO.chk();
    }
    btn.onclick = async ()=>{
        const idx = judgeTc.selectedIndex;
        switch (idx) {
        case 0:
            setPyIO(evalIO);
            evalIO.input = evalStdin.innerText ? evalStdin.innerText.split(/\r?\n/) : [];
            output.innerText = '';
            wrappedRun();
            break;
        case 1:
            setPyIO(judgeIO);
            let predicate = 'passed';
            for (let tcId = 0; tcId < cbtns.length; ++tcId) {
                if (!judge(tcId)) {
                    predicate = `failed (testcase ${tcId + 1})`;
                    break;
                }
            }
            const submitResp = await fetch('/submit', {
                method: 'POST',
                body: JSON.stringify({
                    pass: predicate === 'passed',
                    problem: parseInt((x=>x.slice(x.lastIndexOf('/') + 1))(window.location.pathname)),
                }),
                headers: { 'content-type': 'application/json' },
            });
            const submitJson = await submitResp.json();
            const status = submitJson?.status === 'success' ? "succeeded" : "failed";
            const err = submitJson?.error ? ` {submitJson.error}` : "";
            alert(`Judge result: ${predicate}; Submission ${status}.${err}`)
            break;
        default:
            setPyIO(judgeIO);
            alert(judge(idx - 2) ? 'pass' : 'fail');
            break;
        }
    };
    btn.innerText = 'Run';
    btn.removeAttribute('disabled');
});
