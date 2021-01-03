from ..log import loggable, LogManager, LogWriterStyle

@loggable('crrcan')
class LogCrrcan(LogManager):

    undecoded_by_event_id = {}
    internal_writers = {}
    external_writers = {}

    def on(self):
        count_d = self.employ_sentinels('***/Client.decode_json', nickname='decode')
        count_s = self.employ_sentinels('***/Client.send_json', nickname='send')
        count_fs = self.employ_sentinels('***/App.process_HTTP_request', nickname='first_start')
        count_fe = self.employ_sentinels('app.py/websocket_event', nickname='first_end')
        if count_d != 1 or count_s != 1:
            self.off()
        else:
            super().on()

    def off(self):
        self.dismiss_all_sentinels()
        super().off()


    def on_event(self, event):
        if self.state:
            if event.entering('first_start') and event.arg('path') == '/mupf/bootstrap':
                self._log_data(0, 0, "[0, 0, '*first*', {'args': (), 'kwargs': {'_user_feature': (2+2 == 4)}}]")
                self.dissmiss_sentinel('first_start')
            elif event.entering('first_end') and event.args[0] == 'websocket received result of *first*':
                self._log_data(1, 0, event.kwargs['msg'])
                self.dissmiss_sentinel('first_end')
            elif event.entering('decode'):
                LogCrrcan.undecoded_by_event_id[event.call_id] = event.arg('raw_json')
            elif event.exiting('decode'):
                self._log_data(event.result[0], event.result[1], LogCrrcan.undecoded_by_event_id[event.call_id])
                del LogCrrcan.undecoded_by_event_id[event.call_id]
            elif event.entering('send'):
                self._log_data(event.arg('json')[0], event.arg('json')[1], repr(event.arg('json')))

    def _log_data(self, mode, ccid, text):
        if mode >= 5:
            mode -= 5
            style = LogWriterStyle.outer+LogWriterStyle.rarr
            writers = LogCrrcan.external_writers
        else:
            style = LogWriterStyle.inner+LogWriterStyle.larr
            writers = LogCrrcan.internal_writers

        if mode == 0:
            if ccid in writers:
                wr = writers[ccid]
            else:
                wr = self.new_writer(style=LogWriterStyle.multi_line+style, group='crrc')
                writers[ccid] = wr
            wr.write(text)
        elif mode == 1:
            if ccid in writers:
                wr = writers[ccid]
                wr.write(text, finish=True)
                self.delete_writer(wr)
            else:
                wr = self.new_writer(style=LogWriterStyle.multi_line+style, group='crrc')
                wr.write('**Unmatched msg**')
                wr.write(text, finish=True)
                self.delete_writer(wr)
        elif mode == 2:
            wr = self.new_writer(style=LogWriterStyle.single_line+style, group='crrc')
            wr.write(text)
            self.delete_writer(wr)
