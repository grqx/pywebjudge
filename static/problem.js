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
    function setPyIO(py, o) {
        py.setStdin({stdin: ()=>o[0]()});
        py.setStdout({batched: l=>o[1](l)});
        py.setStderr({batched: l=>o[2](l)});
    }

    const evalIO = [
        function () { return this[3].shift(); },
        function (l) { output.innerText += l + '\n'; },
        function () { if (!this[5]) { this[5] = true; alert('stderr is ignored in judge environment. Please use stdout instead!'); } },
        null,
        null,
        false,
    ];

    const judgeIO = [
        function () { return this[3].shift(); },
        function (l) { this[4].push(l); },
        function () { if (!this[5]) { this[5] = true; alert('stderr is ignored in judge environment. Please use stdout instead!'); } },
        [],
        [],
        false,
    ];

    setPyIO(pyodide, evalIO);
    pyodide.setStderr({ batched: 0 })
    btn.removeAttribute('disabled');
    btn.innerText = 'Run';
    btn.onclick = ()=>{
        evalIO[3] = evalStdin.innerText.split(/\r?\n/);
        output.innerText = '';
        pyodide.runPython(userCode.innerText);
    };
});
