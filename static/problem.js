// TODO: redirect py error
document.addEventListener('DOMContentLoaded', async e=>{
    const userCode = document.getElementById('user-code');
    const btn = document.getElementById('run');
    const evalStdin = document.getElementById('eval-stdin');
    const output = document.getElementById('output');
    const cbtns = document.querySelectorAll('.testcase button.cbtn');
    const judgeTc = document.getElementById('judge-tc');
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

    const pyodide = await loadPyodide({});

    function setPyIO(py, o) {
        py.setStdin({stdin: ()=>o[0]()});
        py.setStdout({batched: l=>o[1](l)});
        py.setStderr({batched: l=>o[2](l)});
    }

    function judge(tcId) {
        const tc = cbtns[tcId].closest('.testcase');
        const tcIn = tc.querySelector('.tc-in')?.innerText;
        const tcOut = tc.querySelector('.tc-out')?.innerText;
        judgeIO.input = tcIn ? tcIn.split(/\r?\n/) : [];
        judgeIO.output = [];
        judgeIO.checkOut = tcOut ? tcOut.split(/\r?\n/) : [];
        pyodide.runPython(userCode.innerText);
        return judgeIO.chk();
    }
    btn.onclick = ()=>{
        const idx = judgeTc.selectedIndex;
        switch (idx) {
        case 0:
            setPyIO(pyodide, evalIO);
            evalIO.input = evalStdin.innerText ? evalStdin.innerText.split(/\r?\n/) : [];
            output.innerText = '';
            pyodide.runPython(userCode.innerText);
            break;
        case 1:
            setPyIO(pyodide, judgeIO);
            for (let tcId = 0; tcId < cbtns.length; ++tcId)
                alert(judge(tcId) ? 'pass' : 'fail');
            break;
        default:
            setPyIO(pyodide, judgeIO);
            alert(judge(idx - 2) ? 'pass' : 'fail');
            break;
        }
    };
    btn.innerText = 'Run';
    btn.removeAttribute('disabled');
});
