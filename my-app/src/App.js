import React, {useState} from "react";
import {Button, Textarea} from "evergreen-ui";
import "./App.css";

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
      <h1 className="title">Sentence Compressor</h1>
      <p className="subtitle">Created by Marisa A. and Mian U.</p>
      <div className="fields">
        <Textarea
          onChange={({target: {value}}) => setVal(value)}
          placeholder="Your text here..."
          value={val}
        />
        <Button onClick={handleClick}>Compress</Button>
      </div>
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
