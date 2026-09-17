// Avance Masivo: marca UNA partida en VARIAS casas de un jalón. Hospeda
// Calandria.Api/ui/avance-masivo.html, mismo patrón que FormClientesWeb.cs.
// Sólo llama a /api/avances/jerarquico, /api/destajos/resumen-casas (lectura)
// y /api/avances/partida (el mismo upsert que ya usa FormHardProgress) —
// nunca toca ActivacionTareasRuta ni ninguna tabla de Destajos/Compras.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using Newtonsoft.Json;
using Newtonsoft.Json.Serialization;

namespace DynamicSepticSystem
{
    public class FormAvanceMasivoWeb : Form
    {
        private WebView2 webAvance;

        private static readonly JsonSerializerSettings CamelCaseSettings =
            new JsonSerializerSettings { ContractResolver = new CamelCasePropertyNamesContractResolver() };

        private static string CacheDir => Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Calandria", "ui");

        private static string CacheHtml => Path.Combine(CacheDir, "avance-masivo.html");

        public FormAvanceMasivoWeb()
        {
            Text = "Avance Masivo - Sistema CalandriaSys";
            StartPosition = FormStartPosition.CenterScreen;
            Size = new Size(1000, 760);
            MinimumSize = new Size(760, 560);
            BackColor = Color.White;
            ThemeManager.AplicarIconoPorDefecto(this);

            webAvance = new WebView2 { Dock = DockStyle.Fill, BackColor = Color.White };
            Controls.Add(webAvance);

            webAvance.CoreWebView2InitializationCompleted += WebAvance_Init;
            _ = IniciarWebView2Async();
        }

        private async Task IniciarWebView2Async()
        {
            try
            {
                string userDataFolder = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "Calandria", "WebView2AvanceMasivo");
                var entorno = await CoreWebView2Environment.CreateAsync(null, userDataFolder, null);
                await webAvance.EnsureCoreWebView2Async(entorno);
            }
            catch (Exception ex)
            {
                ErrorLogger.RegistrarMensaje("AvanceMasivoWeb", "WebView2 no pudo iniciar: " + ex.Message);
                MessageBox.Show("No se pudo iniciar el módulo de Avance Masivo:\n\n" + ex.Message,
                    "CalandriaSys", MessageBoxButtons.OK, MessageBoxIcon.Error);
                if (!IsDisposed) Close();
            }
        }

        private void WebAvance_Init(object sender, CoreWebView2InitializationCompletedEventArgs e)
        {
            if (!e.IsSuccess)
            {
                ErrorLogger.RegistrarMensaje("AvanceMasivoWeb", "WebView2 no inicializó: " + e.InitializationException);
                MessageBox.Show("No se pudo iniciar el módulo de Avance Masivo.", "CalandriaSys",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                if (!IsDisposed) Close();
                return;
            }

            var core = webAvance.CoreWebView2;
            core.Settings.AreDefaultContextMenusEnabled = Debugger.IsAttached;
            core.Settings.AreDevToolsEnabled = Debugger.IsAttached;
            core.Settings.IsStatusBarEnabled = false;

            core.WebMessageReceived += WebAvance_Mensaje;

            _ = CargarHtmlAsync();
        }

        private async Task CargarHtmlAsync()
        {
            string html = null;
            try { html = await Task.Run(() => ObtenerHtml()); }
            catch (Exception ex) { ErrorLogger.RegistrarMensaje("AvanceMasivoWeb", "Fallo cargando la página: " + ex.Message); }

            if (IsDisposed || webAvance?.CoreWebView2 == null) return;
            if (html == null)
            {
                MessageBox.Show("No se pudo descargar la interfaz web de Avance Masivo.", "CalandriaSys",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                Close();
                return;
            }
            webAvance.CoreWebView2.NavigateToString(html);
        }

        private static string Sha256(byte[] d)
        {
            using (var sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(d)).Replace("-", "").ToLowerInvariant();
        }

        private class VersionUi { public string hash; public int bytes; }

        private static string ObtenerHtml()
        {
            string cache = File.Exists(CacheHtml) ? File.ReadAllText(CacheHtml, Encoding.UTF8) : null;
            try
            {
                var ver = ApiClient.Get<VersionUi>("/api/ui/avance-masivo/version");
                if (cache != null && ver != null && ver.hash == Sha256(Encoding.UTF8.GetBytes(cache)))
                    return cache;

                var datos = ApiClient.GetBytes("/api/ui/avance-masivo");
                if (datos != null && datos.Length > 0)
                {
                    string html = Encoding.UTF8.GetString(datos);
                    try { Directory.CreateDirectory(CacheDir); File.WriteAllText(CacheHtml, html, new UTF8Encoding(false)); }
                    catch { /* la caché es un extra; si falla, seguimos */ }
                    return html;
                }
            }
            catch (Exception ex)
            {
                ErrorLogger.RegistrarMensaje("AvanceMasivoWeb", "No se pudo traer la UI del API: " + ex.Message);
            }
            return cache;
        }

        // ------------------------------------------------------------------
        // Puente C# -> JS
        // ------------------------------------------------------------------

        private void Push(object payload)
        {
            if (webAvance?.CoreWebView2 == null) return;
            try { webAvance.CoreWebView2.PostWebMessageAsJson(JsonConvert.SerializeObject(payload, CamelCaseSettings)); }
            catch (Exception ex) { ErrorLogger.RegistrarMensaje("AvanceMasivoWeb", "Fallo al enviar datos a la página: " + ex.Message); }
        }

        private void PushError(string mensaje)
        {
            if (webAvance?.CoreWebView2 == null) return;
            try { webAvance.CoreWebView2.PostWebMessageAsJson(JsonConvert.SerializeObject(new { tipo = "error", mensaje }, CamelCaseSettings)); }
            catch { /* si ni el aviso de error sale, no hay más que intentar */ }
        }

        private static string MensajeDe(ApiException ex)
        {
            try
            {
                var cuerpo = JsonConvert.DeserializeAnonymousType(ex.Cuerpo, new { Message = "" });
                return string.IsNullOrEmpty(cuerpo?.Message) ? ex.Cuerpo : cuerpo.Message;
            }
            catch { return ex.Cuerpo; }
        }

        private void ManejarErrorApi(Exception ex, string contexto)
        {
            var apiEx = ex as ApiException;
            string msg = apiEx != null ? MensajeDe(apiEx) : ex.Message;
            ErrorLogger.RegistrarMensaje("AvanceMasivoWeb", contexto + ": " + msg);
            PushError(contexto + ": " + msg);
        }

        // ------------------------------------------------------------------
        // Puente JS -> C#
        // ------------------------------------------------------------------

        private class MsgAccion { public string accion; }
        private class MsgCasaJs { public string manzana; public string lote; public string prototipo; }
        private class MsgAplicarAvance
        {
            public int wbs;
            public string padre;
            public double costoTunera;
            public double costoCalandra;
            public double avance;
            public List<MsgCasaJs> casas;
        }

        private void WebAvance_Mensaje(object sender, CoreWebView2WebMessageReceivedEventArgs e)
        {
            string json = e.WebMessageAsJson;
            MsgAccion m;
            try { m = JsonConvert.DeserializeObject<MsgAccion>(json); }
            catch { return; }
            if (m?.accion == null) return;

            // BeginInvoke: no despachar dentro del propio callback COM de WebView2.
            BeginInvoke((Action)(() => DespacharMensaje(m.accion, json)));
        }

        private void DespacharMensaje(string accion, string json)
        {
            try
            {
                switch (accion)
                {
                    case "cargar-datos": CargarDatosWeb(); break;
                    case "aplicar-avance":
                        { var d = JsonConvert.DeserializeObject<MsgAplicarAvance>(json); AplicarAvanceWeb(d); }
                        break;
                    case "volver":
                        Close();
                        break;
                    default:
                        ErrorLogger.RegistrarMensaje("AvanceMasivoWeb", "Acción desconocida desde la página: " + accion);
                        break;
                }
            }
            catch (Exception ex)
            {
                ManejarErrorApi(ex, "No se pudo completar la acción solicitada");
            }
        }

        private void CargarDatosWeb()
        {
            try
            {
                // Catálogo de partidas con el costo de ambos prototipos: el WBS es
                // estable entre llamadas porque el ORDER BY de /api/avances/jerarquico
                // no depende del prototipo (ver AvancesController.Jerarquico).
                var conCalandra = ApiClient.Get<JerarquicoAvanceApi>("/api/avances/jerarquico?manzana=&lote=&prototipo=CALANDRA");
                var conTunera = ApiClient.Get<JerarquicoAvanceApi>("/api/avances/jerarquico?manzana=&lote=&prototipo=TUNERA");
                var costoTuneraPorWbs = (conTunera?.Partidas ?? new List<PartidaAvanceApi>()).ToDictionary(p => p.Wbs, p => p.ImporteTotal);

                var partidas = (conCalandra?.Partidas ?? new List<PartidaAvanceApi>())
                    .Select(p => new
                    {
                        wbs = p.Wbs,
                        etiqueta = $"{p.Etapa} > {p.Partida}",
                        padre = p.Padre,
                        costoCalandra = p.ImporteTotal,
                        costoTunera = costoTuneraPorWbs.TryGetValue(p.Wbs, out var ct) ? ct : p.ImporteTotal
                    })
                    .OrderBy(p => p.etiqueta)
                    .ToList();

                // Mismo listado de sólo lectura que usa el mapa del panel principal.
                var resumen = ApiClient.Get<List<ResumenCasaApi>>("/api/destajos/resumen-casas") ?? new List<ResumenCasaApi>();
                var casas = resumen
                    .OrderBy(c => c.Manzana).ThenBy(c => c.Lote)
                    .Select(c => new { manzana = c.Manzana, lote = c.Lote, prototipo = c.Prototipo })
                    .ToList();

                Push(new { tipo = "datos", partidas, casas });
            }
            catch (Exception ex)
            {
                ManejarErrorApi(ex, "No se pudieron cargar los datos");
            }
        }

        private void AplicarAvanceWeb(MsgAplicarAvance d)
        {
            if (d?.casas == null || d.casas.Count == 0)
            {
                PushError("No se recibieron casas a actualizar.");
                return;
            }

            int ok = 0;
            var errores = new List<string>();

            foreach (var c in d.casas)
            {
                try
                {
                    bool esTunera = (c.prototipo ?? "").ToUpperInvariant().Contains("TUNERA");
                    double costo = esTunera ? d.costoTunera : d.costoCalandra;
                    double ejecutado = costo * (d.avance / 100.0);

                    // Mismo endpoint que GuardarAvancePartidaEnBD en FormHardProgress.
                    ApiClient.Post("/api/avances/partida", new
                    {
                        Manzana = c.manzana,
                        Lote = c.lote,
                        Prototipo = c.prototipo,
                        Wbs = d.wbs,
                        AvancePorcentaje = d.avance,
                        Concepto = d.padre ?? "",
                        ImporteTotal = costo,
                        ImporteEjecutado = ejecutado
                    });
                    ok++;
                }
                catch (Exception ex)
                {
                    var apiEx = ex as ApiException;
                    string msg = apiEx != null ? MensajeDe(apiEx) : ex.Message;
                    errores.Add($"M{c.manzana}-L{c.lote}: {msg}");
                }
            }

            Push(new { tipo = "resultado", ok, errores });
        }
    }
}
