document.addEventListener('DOMContentLoaded', async e=>{
    const userCode = document.getElementById('user-code');
    const btn = document.getElementById('run');
    const evalStdin = document.getElementById('eval-stdin');
    const output = document.getElementById('output');
    const cbtns = document.querySelectorAll('.testcase button.cbtn');

    function cBtnOnClick() {
        const tcIn = this.closest('.testcase').querySelector('.tc-in')
        evalStdin.innerText = tcIn.innerText;
    }

    for (const cbtn of cbtns)
        cbtn.onclick = cBtnOnClick;

    const pyodide = await loadPyodide({});
    let currentIO;
    function setPyIO(py, o) {
        currentIO = o;
        py.setStdin({stdin: ()=>o[0]()});
        py.setStdout({batched: l=>o[1](l)});
        py.setStderr({batched: l=>o[2](l)});
    }

    const evalIO = {
        0: function () { return this.input.shift(); },
        1: function (l) { output.innerText += l + '\n'; },
        2: function () {
            if (!this[5]) {
                this[5] = true;
                alert('stderr is ignored in judge environment. Please use stdout instead!'); 
            }
        },
        input: null,
        output: null,
        warned: false,
    };

    const judgeIO = {
        0: function () { return this[3].shift(); },
        1: function (l) { this[4].push(l); },
        2: function () {
            if (!this[5]) {
                this[5] = true;
                alert('stderr is ignored in judge environment. Please use stdout instead!');
            }
        },
        3: function () {
            if (this.checkOut === null) return;
            // ...
        },
        input: [],
        output: [],
        warned: false,
        checkOut: null,
    };

    setPyIO(pyodide, evalIO);
    pyodide.setStderr({ batched: 0 })
    btn.removeAttribute('disabled');
    btn.innerText = 'Run';
    btn.onclick = ()=>{
        currentIO.input = evalStdin.innerText.split(/\r?\n/);
        output.innerText = '';
        pyodide.runPython(userCode.innerText);
        currentIO[3]();
    };
});
