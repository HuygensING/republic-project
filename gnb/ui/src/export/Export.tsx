export default function Export() {
  function exportSelection() {
    console.log('export');
  }

  return <div>
    <button
      type="button"
      onClick={exportSelection}
      className="btn btn-info float-right"
    >
      Export <i className="fas fa-sign-out-alt"/>
    </button>
  </div>
}
