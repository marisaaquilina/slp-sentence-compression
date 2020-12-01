import React, {useState} from "react";

function App() {
  const [val, setVal] = useState("");
  const [resp, setResp] = useState(null);
  const handleClick = async () => {
    setResp(null);
    const response = await fetch(`http://127.0.0.1:5000/?sentence=${encodeURIComponent(val)}`);
    setResp(await response.json());
  };

  return (
    <div className="App">
      <h1>CSC 482 - Project 2: Sentence Compression</h1>
      <p>Marisa Aquilina, Mian Uddin</p>
      <input value={val} onChange={({target: {value}}) => setVal(value)}/>
      <button onClick={handleClick}>Compress!</button>
      {resp && (
        <>
          <h2>Response</h2>
          <h3>Message</h3>
          <p>{resp.msg}</p>
          <h3>Compressions</h3>
          {resp.compressions
            ? <ul>{resp.compressions.map((c, i) => <li k={i}>{c}</li>)}</ul>
            : <em>null</em>
          }
        </>
      )}
    </div>
  );
}

export default App;
