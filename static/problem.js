document.addEventListener('DOMContentLoaded', async e=>{
    const userCode = document.getElementById('user-code');
    const btn = document.getElementById('run');
    const output = document.getElementById('output');
    let warned = false;
    const outbuf = [];
    const pyodide = await loadPyodide({
        stdin: ()=>{ return 'dummy stdin'; },
        stdout: l=>{ outbuf.push(l); output.innerText += (l + '\n'); },
        stderr: l=>{ if (!warned) {warned = true; alert('stderr is ignored. Please use stdout instead!')} },
    });
    btn.removeAttribute('disabled');
    btn.innerText = 'Run';
    btn.onclick = ()=>{
        output.innerText = '';
        pyodide.runPython(userCode.innerText);
    };
    btn.classList.remove('hidden');
});
