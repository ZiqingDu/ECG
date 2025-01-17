import tensorflow as tf


class CNNGraph:

    def __init__(self, input_size_1: int,input_size_2: int, output_size: int,learning_rate=0.0001,
                        dropout: float = 0.2) -> None:

        ## A neural network architecture:
        self.input_size_1 = input_size_1
        self.input_size_2 = input_size_2
        self.output_size = output_size

        ## Graph object trainable parameters:
        self.graph = tf.Graph()
        self.X: tf.placeholder
        self.Y: tf.placeholder
        self.keep_prob: tf.placeholder
        self.projection: tf.Tensor
        self.loss: tf.Tensor
        self.grad_op: tf.Tensor
        self.learning_rate=learning_rate

            
    def r_block(self,in_layer,k,keep_prob,is_training):
        x = tf.layers.batch_normalization(in_layer)
        x = tf.nn.relu(x)
        x = tf.layers.dropout(x, rate=keep_prob, training=is_training)
        x = tf.layers.conv1d(x,64*k,16,padding='same',kernel_initializer=tf.glorot_uniform_initializer())
        x = tf.layers.batch_normalization(x)
        x = tf.nn.relu(x)
        x = tf.layers.dropout(x, rate=keep_prob, training=is_training)
        x = tf.layers.conv1d(x,64*k,16,padding='same',kernel_initializer=tf.glorot_uniform_initializer())
        x = tf.add(x,in_layer)
        return x

    def subsampling_r_block(self,in_layer,k,keep_prob,is_training):
        x = tf.layers.batch_normalization(in_layer)
        x = tf.nn.relu(x)
        x = tf.layers.dropout(x, rate=keep_prob, training=is_training)
        x = tf.layers.conv1d(x,64*k,16,kernel_initializer=tf.glorot_uniform_initializer(),padding='same')
        x = tf.layers.batch_normalization(x)
        x = tf.nn.relu(x)
        x = tf.layers.dropout(x, rate=keep_prob, training=is_training)
        x = tf.layers.conv1d(x, 64*k, 1, strides=2,kernel_initializer=tf.glorot_uniform_initializer())
        pool = tf.layers.max_pooling1d(in_layer,1,strides=2)
        x = tf.add(x,pool)
        return x

    def stacked(self,x,keep_prob):
        # Define a scope for reusing the variables
        with tf.variable_scope('ConvNet'): 
            is_training =tf.cond( keep_prob<1.0,lambda:True,lambda: False)

            act1 = tf.layers.conv1d(x, 64, 16, padding='same',kernel_initializer=tf.glorot_uniform_initializer())
            x = tf.layers.batch_normalization(act1)
            x = tf.nn.relu(x)

            x = tf.layers.conv1d(x, 64, 16, padding='same',kernel_initializer=tf.glorot_uniform_initializer())
            x = tf.layers.batch_normalization(x)
            x = tf.nn.relu(x)

            x = tf.layers.dropout(x, rate=keep_prob, training=is_training)
            x1 = tf.layers.conv1d(x, 64, 1, strides=2,kernel_initializer=tf.glorot_uniform_initializer())

            x2 = tf.layers.max_pooling1d(act1,2,strides=2)
            x = tf.add(x1,x2)

            k=1
            for i in range(1,3,1):
                if i%2 ==0:
                    k+=1
                x=tf.layers.conv1d(x,64*k,16,padding='same',kernel_initializer=tf.glorot_uniform_initializer())
                x=self.r_block(x,k,keep_prob,is_training)
                x=self.subsampling_r_block(x,k,keep_prob,is_training)

            x = tf.layers.batch_normalization(x)
            x = tf.nn.relu(x)
            x = tf.contrib.layers.flatten(x)
            out = tf.layers.dense(x, 4,kernel_initializer=tf.glorot_uniform_initializer())
        return out



    def Graph(self) -> tf.Tensor:
        with tf.Graph().as_default() as self.graph:
            self.X = tf.placeholder(tf.float32, shape=(None, self.input_size_1,self.input_size_2), name="Inputs")
            self.Y = tf.placeholder(tf.float32, shape=(None, self.output_size), name="Output")
            self.keep_prob = tf.placeholder(tf.float32)

            #for the training part
            self.projection = self.stacked(self.X,  self.keep_prob)
            self.loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=self.projection, labels=self.Y))
            self.adam_op = tf.train.AdamOptimizer(self.learning_rate)
            self.cnn_grad_op = self.adam_op.compute_gradients(self.loss)
            self.sub_grad_op = self.adam_op.minimize(self.loss)             
            #self.grad_placeholder = [(tf.placeholder("float", shape=gradt[1].get_shape()), gradt[1]) for gradt in self.cnn_grad_op]

            #self.apply_op = self.adam_op.apply_gradients(self.grad_placeholder)
            self.max_projection = tf.argmax(self.projection, 1)
            self.projection_1hot = tf.one_hot(self.max_projection, depth = int(self.output_size))
            self.accuracy = tf.reduce_mean(tf.cast(tf.equal(self.max_projection, tf.argmax(self.Y, 1)), tf.float32))
            avg_grads_and_vars = []
            self._grad_placeholders = []
            for grad, var in self.cnn_grad_op:
                grad_ph = tf.placeholder(grad.dtype, grad.shape)
                self._grad_placeholders.append(grad_ph)
                avg_grads_and_vars.append((grad_ph, var))
            self._grad_op = [x[0] for x in self.cnn_grad_op]
            self._train_op = self.adam_op.apply_gradients(avg_grads_and_vars)
            self._gradients = [] # list to store gradients
