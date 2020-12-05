import React, {useState} from "react";
import {Button, Textarea, Spinner} from "evergreen-ui";
import "./App.css";

function App() {
  const [val, setVal] = useState("");
  const [resp, setResp] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toggle, setToggle] = useState(false);
  const handleClick = async () => {
    setResp(null);
    setLoading(true);
    try {
      const response = await fetch(`http://127.0.0.1:5000/?sentence=${encodeURIComponent(val)}`);
      const respJSON = await response.json();
      setLoading(false);
      setResp(respJSON);
    } catch (error) {
      setLoading(false);
      setResp({"msg": error.message, "compressions": null});
    }
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
        <Button className="btn" onClick={handleClick}>Compress</Button>
      </div>
      {loading && (
        <Spinner className="spinner" />
      )}
      {resp && (
        <>
          <h2>Response</h2>
          <p>The server returned <span className="length">{resp.compressions ? resp.compressions.length : 0}</span> possible compressions. {resp.compressions && <span>Here are <a className="toggle" onClick={() => setToggle(!toggle)}>{toggle ? "all the": "the top"}</a> compressions:</span>}</p>
          {resp.compressions &&
            <div>{resp.compressions.slice(0, toggle ? resp.compressions.length : 5).map((c, i) => <div className="pair"><span className="prob">{Math.round((c[0] + Number.EPSILON) * 100) / 100}</span><span>{c[1]}</span></div>)}</div>
          }
          <p className="srvmsg">{resp.msg}</p>
        </>
      )}
    </div>
  );
}

export default App;
